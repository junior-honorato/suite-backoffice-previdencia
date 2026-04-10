import streamlit as st
import pandas as pd
import io
import re
import msoffcrypto
import gc

# --- CONFIGURAÇÃO GLOBAL DA PÁGINA ---
st.set_page_config(page_title="Suíte Operações VGBL", page_icon="🏦", layout="centered")


# ==============================================================================
# MÓDULO 1: CONCILIADOR DE PORTABILIDADE (TXT)
# ==============================================================================
POS_INICIO_VAL = 49
POS_FIM_VAL = 63

def format_brl(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    reais = cents // 100
    cent = cents % 100
    reais_str = f"{reais:,}".replace(",", ".")
    return f"{sign}R$ {reais_str},{cent:02d}"

def achar_grupo_numerico_na_janela(linha: str):
    i0, j0 = POS_INICIO_VAL - 1, POS_FIM_VAL
    if i0 >= len(linha): return None
    win = linha[i0:j0]
    k = None
    for pos, ch in enumerate(win):
        if ch.isdigit():
            k = pos; break
    if k is None: return None
    m = k + 1
    while m < len(win) and win[m].isdigit(): m += 1
    digits = win[k:m]
    if not digits: return None
    return i0 + k, i0 + m, int(digits)

def extrair_valores(conteudo: str):
    linhas = conteudo.split("\r\n")
    valores = []
    for idx, ln in enumerate(linhas, start=1):
        if idx < 3 or not ln.strip(): continue
        grp = achar_grupo_numerico_na_janela(ln)
        if grp: valores.append((idx, grp[2]))
    return valores

def somar_total(conteudo: str) -> int:
    return sum(v for _, v in extrair_valores(conteudo))

def ajustar_primeira_linha(conteudo: str, ajuste_centavos: int) -> str:
    linhas = conteudo.split("\r\n")
    for idx, ln in enumerate(linhas, start=1):
        if idx < 3 or not ln.strip(): continue
        grp = achar_grupo_numerico_na_janela(ln)
        if not grp: continue
        ini, fim, val_atual = grp
        novo_valor = max(0, val_atual - ajuste_centavos)
        width = fim - ini
        novo_digits = str(novo_valor).rjust(width, "0")
        if len(novo_digits) > width:
            raise ValueError("Ajuste excede a largura da janela.")
        linhas[idx - 1] = ln[:ini] + novo_digits + ln[fim:]
        return "\r\n".join(linhas)
    raise ValueError("Nenhuma linha de movimento encontrada.")

def parse_valor_correto(valor_str: str) -> int:
    s = "".join(ch for ch in valor_str if ch.isdigit() or ch in ".,")
    digits = "".join(ch for ch in s if ch.isdigit())
    if not digits: raise ValueError("Valor inválido.")
    return int(digits)

def renderizar_conciliador():
    st.title("🧮 Ajuste do valor Portabilidade de Saída - SIDE")
    st.markdown("Ajuste matemático de dízimas e arredondamentos na Portabilidade de Saída.")
    st.divider()

    uploaded_file = st.file_uploader("Arraste o arquivo .TXT desbalanceado aqui", type=["txt"])

    if uploaded_file is not None:
        conteudo_bytes = uploaded_file.getvalue()
        try:
            conteudo_str = conteudo_bytes.decode("cp1252")
        except:
            conteudo_str = conteudo_bytes.decode("latin-1")
        
        total_incorreto_cents = somar_total(conteudo_str)
        
        st.subheader("Análise do Arquivo")
        st.metric(label="Valor Total Encontrado", value=format_brl(total_incorreto_cents))
        
        st.info("Informe o valor exato que o arquivo deveria ter para fechamento.")
        valor_correto_input = st.text_input("Valor Correto (Ex: 12.345,67)", "")
        
        if st.button("Aplicar Ajuste e Validar", type="primary"):
            if not valor_correto_input:
                st.warning("Por favor, informe o valor correto.")
            else:
                try:
                    vcor_cents = parse_valor_correto(valor_correto_input)
                    ajuste_cents = total_incorreto_cents - vcor_cents
                    
                    if abs(ajuste_cents) > 100:
                        st.error(f"🚨 **Trava de Segurança:** A diferença é de {format_brl(ajuste_cents)}. Deltas superiores a R$ 1,00 exigem revisão manual.")
                    else:
                        conteudo_ajustado = ajustar_primeira_linha(conteudo_str, ajuste_cents)
                        total_pos = somar_total(conteudo_ajustado)
                        
                        if total_pos != vcor_cents:
                            st.error("Falha na revalidação. O layout pode estar corrompido.")
                        else:
                            st.success("✅ Arquivo ajustado e validado matematicamente com sucesso!")
                            col1, col2 = st.columns(2)
                            col1.metric("Ajuste Aplicado", format_brl(ajuste_cents))
                            col2.metric("Novo Valor Total", format_brl(total_pos))
                            
                            novo_arquivo_bytes = conteudo_ajustado.encode("cp1252")
                            nome_original = uploaded_file.name.replace(".txt", "")
                            
                            st.download_button(
                                label="📥 Baixar Arquivo Ajustado (SIDE)",
                                data=novo_arquivo_bytes,
                                file_name=f"{nome_original}_alterado_SIDE.txt",
                                mime="text/plain"
                            )
                            # LGPD & Memory Optimization: Explicit cleanup
                            del conteudo_bytes, conteudo_str, conteudo_ajustado, novo_arquivo_bytes
                            gc.collect()
                except Exception as e:
                    st.error(f"Erro ao processar: {e}")

# ==============================================================================
# MÓDULO 2: CONVERSOR EXCEL -> TXT
# ==============================================================================
DATE_RX = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")
MONEY_RXS = [
    re.compile(r"^\s*R\$\s*\d{1,3}(?:\.\d{3})*,\d{2}\s*$"),
    re.compile(r"^\s*R\$\s*\d+,\d{2}\s*$"),
    re.compile(r"^\s*\d{1,3}(?:\.\d{3})*,\d{2}\s*$"),
    re.compile(r"^\s*\d+,\d{2}\s*$"),
]
STRING_FIXA   = "03654036541584001"
TAMANHO_LINHA = 1000
ESPACO_EXTRA  = " " * (TAMANHO_LINHA - 63)
SEQ_INICIAL   = 3

def is_date_like(val):
    if pd.isna(val): return False
    if isinstance(val, pd.Timestamp): return True
    return bool(DATE_RX.match(str(val).strip()))

def parse_date_to_yyyymmdd(val):
    if pd.isna(val): return ""
    if isinstance(val, pd.Timestamp): return val.strftime("%Y%m%d")
    s = str(val).strip()
    m = DATE_RX.match(s)
    if m:
        d, mo, y = m.groups()
        return f"{y}{mo}{d}"
    try:
        return pd.to_datetime(s, dayfirst=True, errors="raise").strftime("%Y%m%d")
    except:
        return ""

def is_money_like(val):
    if pd.isna(val): return False
    if isinstance(val, (int, float)): return True
    return any(rx.match(str(val).strip()) for rx in MONEY_RXS)

def parse_money_to_centavos_int(val):
    if pd.isna(val): return 0
    if isinstance(val, (int, float)): return int(round(float(val) * 100))
    s = str(val).replace("R$", "").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return int(round(float(s) * 100))
    except:
        return 0

def detect_columns(df):
    date_scores = {c: df[c].apply(is_date_like).mean() for c in df.columns}
    money_scores = {c: df[c].apply(is_money_like).mean() for c in df.columns}
    date_col = max(date_scores, key=date_scores.get)
    best_pair, best_score = (None, None), -1
    cols = list(df.columns)
    for i in range(len(cols)-1):
        c1, c2 = cols[i], cols[i+1]
        score = money_scores[c1] + money_scores[c2]
        if score > best_score:
            best_pair, best_score = (c1, c2), score
    return date_col, best_pair[0], best_pair[1]

def standardize_dataframe(df):
    date_col, m1, m2 = detect_columns(df)
    if not date_col or not m1 or not m2: raise ValueError("Colunas não detectadas.")
    out = pd.DataFrame()
    out["DATA"] = df[date_col].apply(parse_date_to_yyyymmdd)
    out["VALOR 1"] = df[m1].apply(parse_money_to_centavos_int)
    out["VALOR 2"] = df[m2].apply(parse_money_to_centavos_int)
    return out

def remove_possible_total_footer(df):
    if df.empty or "DATA" not in df: return df
    blank_idx = df.index[df["DATA"].eq("")].tolist()
    if not blank_idx: return df
    idx = blank_idx[-1]
    prev = df.drop(index=idx)
    if prev.empty: return df
    try:
        v1 = int(df.loc[idx, "VALOR 1"]); sum1 = int(prev["VALOR 1"].sum())
        if abs(v1 - sum1) <= 1: return prev.reset_index(drop=True)
    except: pass
    return df

def dataframe_to_fixed_txt_string(df):
    linhas = []
    seq = SEQ_INICIAL
    for _, row in df.iterrows():
        data = str(row["DATA"])[:8].rjust(8, "0") if row["DATA"] else "00000000"
        v1 = int(row["VALOR 1"])
        v2 = int(row["VALOR 2"])
        linhas.append(f"02{str(seq).zfill(6)}{STRING_FIXA}{data}{v1:015d}{v2:015d}{ESPACO_EXTRA}")
        seq += 1
    return "\r\n".join(linhas)

def load_excel_secure(uploaded_file, password=""):
    suf = uploaded_file.name.split('.')[-1].lower()
    engine = "openpyxl" if suf == "xlsx" else "xlrd"
    file_bytes = uploaded_file.getvalue()
    if password:
        try:
            f = io.BytesIO(file_bytes)
            office = msoffcrypto.OfficeFile(f)
            office.load_key(password=password)
            decrypted = io.BytesIO()
            office.decrypt(decrypted)
            decrypted.seek(0)
            return pd.read_excel(decrypted, engine=engine)
        except:
            raise ValueError("Senha incorreta.")
    try:
        return pd.read_excel(io.BytesIO(file_bytes), engine=engine)
    except Exception as e:
        if any(h in str(e).lower() for h in ["encrypted", "password"]):
            raise PermissionError("Arquivo protegido.")
        raise ValueError("Formato inválido.")

def renderizar_conversor():
    st.title("📄 Conversor das contribuições em Excel para TXT padrão SIDE")
    st.markdown("Transforma planilhas de contribuição em layout posicional SIDE.")
    st.divider()

    uploaded_file = st.file_uploader("Arraste a planilha Excel aqui (.xls ou .xlsx)", type=["xls", "xlsx"])

    if uploaded_file is not None:
        if 'password' not in st.session_state: st.session_state.password = ""
        try:
            df = load_excel_secure(uploaded_file, password=st.session_state.password)
            st.success("Planilha lida! Padronizando...")
            try:
                std = standardize_dataframe(df)
                sort_key = pd.to_numeric(std["DATA"].replace("", pd.NA), errors="coerce")
                std = std.assign(_key=sort_key).sort_values(by="_key", na_position="last").drop(columns="_key").reset_index(drop=True)
                std = remove_possible_total_footer(std)
                txt_string = dataframe_to_fixed_txt_string(std)
                
                st.metric("Linhas Processadas", len(std))
                st.download_button(
                    label="📥 Baixar Arquivo TXT (Padrão SIDE)",
                    data=txt_string.encode("cp1252"),
                    file_name=f"{uploaded_file.name.rsplit('.', 1)[0]}_padronizado.txt",
                    mime="text/plain",
                    type="primary"
                )
                # LGPD & Memory Optimization: Explicit cleanup
                del df, std, txt_string
                gc.collect()
            except Exception as e:
                st.error(f"Erro na conversão: {e}")
        except PermissionError:
            st.warning("🔒 Este arquivo está protegido por senha.")
            pwd = st.text_input("Digite a senha e aperte Enter:", type="password")
            if pwd:
                st.session_state.password = pwd
                st.rerun()
        except ValueError as ve:
            st.error(str(ve))
            if st.button("Tentar outra senha"):
                st.session_state.password = ""
                st.rerun()

# ==============================================================================
# MOTOR PRINCIPAL (BARRA LATERAL / MENU)
# ==============================================================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2830/2830284.png", width=60) # Ícone genérico de banco
st.sidebar.title("Suíte VGBL")
st.sidebar.markdown("Selecione a ferramenta desejada:")

opcao = st.sidebar.radio(
    "Navegação:",
    ["1. Ajuste valor Portabilidade Saída", "2. Conversor Excel para TXT padrão SIDE"]
)

st.sidebar.divider()
st.sidebar.caption("Ambiente Local | 100% LGPD 🛡️")

# Roteador de Telas
if opcao == "1. Ajuste valor Portabilidade Saída":
    renderizar_conciliador()
elif opcao == "2. Conversor Excel para TXT padrão SIDE":
    renderizar_conversor()
