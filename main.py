import streamlit as st
import pandas as pd
from src.database import init_db, get_total_concursos, inserir_palpite, obter_resultado, listar_todos_palpites, contar_palpites, deletar_palpite
from src.pipeline import ensure_data_loaded, sync_results
from src.generator import generate_palpites, gerar_fechamento, explicar_filtros, PRIMES, BORDER
from src.conferidor import conferir_palpites

st.set_page_config(
    page_title="Lotofácil Analytics",
    page_icon="🎰",
    layout="wide",
)

PRIMES_LIST = sorted(PRIMES)
BORDER_LIST = sorted(BORDER)


def init_app():
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state.db_initialized = True

    if "data_loaded" not in st.session_state:
        with st.spinner("🔄 Verificando e carregando dados históricos..."):
            result = ensure_data_loaded()
            if result["status"] == "ok":
                if "seed_only" in result:
                    st.warning(result["message"])
                elif "message" in result:
                    st.info(result["message"])
            else:
                st.error(result["message"])
        st.session_state.data_loaded = True


def render_sidebar():
    with st.sidebar:
        st.title("🎰 Lotofácil Analytics")
        st.markdown("Sistema inteligente de análise e geração de palpites.")

        st.divider()

        total = get_total_concursos()
        st.metric("📊 Concursos no BD", total)

        if st.button("🔄 Sincronizar Dados", width='stretch', type="primary"):
            with st.spinner("Sincronizando com a API..."):
                result = sync_results()
            if result["status"] == "ok":
                st.success(
                    f"Sincronizado! {result['added']} novos, {result['updated']} atualizados."
                )
                if result.get("errors"):
                    for err in result["errors"]:
                        st.warning(err)
                st.rerun()
            else:
                st.error(result["message"])

        st.divider()
        st.caption(
            "ℹ️ Os palpites gerados são baseados em análises estatísticas "
            "e não garantem prêmios. Jogue com responsabilidade."
        )


def tab_dashboard():
    col1, col2, col3 = st.columns(3)

    total = get_total_concursos()
    ultimo = obter_resultado(total) if total > 0 else None

    col1.metric("Total de Concursos", total)
    col2.metric("Dezenas por Sorteio", "15")
    col3.metric("Faixa de Números", "01 - 25")

    if ultimo:
        st.subheader(f"📅 Último Concurso: {ultimo['concurso']}")
        c = st.columns([1, 3])
        with c[0]:
            dezenas = [int(x) for x in ultimo["dezenas"].split(",")]
            st.write(f"**Data:** {ultimo['data']}")
            st.write("**Dezenas sorteadas:**")
            cols = st.columns(5)
            for i, d in enumerate(dezenas):
                with cols[i % 5]:
                    st.markdown(
                        f"<div style='text-align:center;font-size:1.4rem;font-weight:bold;"
                        f"background:#f0f2f6;border-radius:8px;padding:6px;margin:2px;"
                        f"white-space:nowrap;min-width:2.4rem;display:inline-block;'>{d:02d}</div>",
                        unsafe_allow_html=True,
                    )
    else:
        st.info("Nenhum concurso encontrado no banco de dados. Use o botão Sincronizar na barra lateral.")

    st.divider()

    st.subheader("📖 Informações sobre os Filtros")
    filter_cols = st.columns(2)
    with filter_cols[0]:
        st.markdown("**🔢 Pares vs Ímpares:** 7 pares e 8 ímpares ou vice-versa.")
        st.markdown(f"**🔢 Números Primos:** {PRIMES_LIST} (exatamente 5 ou 6 por aposta)")
    with filter_cols[1]:
        st.markdown(f"**🔲 Moldura (Borda):** {BORDER_LIST}")
        st.markdown("Exatamente 9 ou 10 dezenas na borda do cartão.")
        st.markdown("**🔄 Repetição:** 8 a 10 dezenas repetidas do sorteio anterior.")


def tab_gerador():
    st.subheader("🎯 Gerador de Palpites")
    st.markdown("Gera combinações que atendem aos filtros de: pares/ímpares, primos, moldura e repetição.")

    col1, col2 = st.columns([1, 1])
    with col1:
        concurso_alvo = st.number_input(
            "Número do Concurso Alvo",
            min_value=2,
            max_value=99999,
            value=get_total_concursos() + 1 if get_total_concursos() > 0 else 11,
            step=1,
        )
    with col2:
        quantidade = st.number_input(
            "Quantidade de Palpites",
            min_value=1,
            max_value=100,
            value=10,
            step=1,
        )

    if concurso_alvo > get_total_concursos() + 1 and get_total_concursos() > 0:
        st.warning(
            f"O concurso alvo ({concurso_alvo}) está muito à frente do último concurso ({get_total_concursos()}). "
            "O filtro de repetição usará o concurso anterior disponível."
        )

    if st.button("🚀 Gerar Palpites", type="primary", width='stretch'):
        with st.spinner("Gerando combinações..."):
            try:
                palpites = generate_palpites(concurso_alvo, quantidade)
            except Exception as e:
                st.error(f"Erro ao gerar palpites: {e}")
                return

        if not palpites:
            st.warning(
                f"Nenhuma combinação encontrada com os filtros atuais após 200.000 tentativas. "
                f"Tente novamente ou reduza a quantidade."
            )
            return

        st.success(f"{len(palpites)} palpites gerados com sucesso!")

        resultado_alvo = obter_resultado(concurso_alvo)
        concurso_data = resultado_alvo["data"] if resultado_alvo else ""

        dados = []
        for i, palpite in enumerate(palpites, 1):
            filtros = explicar_filtros(palpite, concurso_alvo)
            palpite_str = ", ".join(f"{d:02d}" for d in palpite)
            dezenas_db = ",".join(str(d) for d in palpite)
            dados.append(
                {
                    "Nº": i,
                    "Concurso": concurso_alvo,
                    "Data": concurso_data,
                    "Dezenas": palpite_str,
                    "Pares": filtros["pares"],
                    "Ímpares": filtros["impares"],
                    "Primos": filtros["primos"],
                    "Moldura": filtros["moldura"],
                    "Repetidos": filtros["repetidos"] if filtros["repetidos"] is not None else "-",
                }
            )
            inserir_palpite(concurso_alvo, dezenas_db, concurso_data)

        df = pd.DataFrame(dados)
        st.dataframe(df, hide_index=True, width='stretch')

        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Baixar CSV",
            data=csv,
            file_name=f"palpites_concurso_{concurso_alvo}.csv",
            mime="text/csv",
        )

    st.divider()

    with st.expander("🔬 Fechamento Avançado (Matriz de 17 a 20 números)", expanded=False):
        st.markdown("Digite sua matriz de números e o sistema gerará todas as combinações válidas de 15 dezenas.")

        col_a, col_b = st.columns([2, 1])
        with col_a:
            matriz_input = st.text_input(
                "Números da matriz (separados por vírgula ou espaço):",
                placeholder="Ex: 01, 02, 03, 05, 07, 08, 10, 11, 13, 15, 17, 18, 20, 21, 22, 23, 25",
            )
        with col_b:
            concurso_fechamento = st.number_input(
                "Concurso alvo (fechamento)",
                min_value=2,
                max_value=99999,
                value=concurso_alvo,
                step=1,
                key="fechamento_concurso",
            )

        if st.button("⚡ Gerar Fechamento", width='stretch'):
            if not matriz_input.strip():
                st.error("Digite os números da matriz.")
                return

            try:
                numeros = []
                for token in matriz_input.replace(",", " ").split():
                    token = token.strip()
                    if token:
                        numeros.append(int(token))

                if len(numeros) < 17 or len(numeros) > 20:
                    st.error(f"A matriz deve ter entre 17 e 20 números (você forneceu {len(numeros)}).")
                    return

                if any(n < 1 or n > 25 for n in numeros):
                    st.error("Todos os números devem estar entre 1 e 25.")
                    return

                with st.spinner("Gerando combinações do fechamento..."):
                    combos = gerar_fechamento(concurso_fechamento, numeros)

                if not combos:
                    st.warning("Nenhuma combinação válida encontrada para esta matriz com os filtros atuais.")
                    return

                st.success(f"{len(combos)} combinações geradas!")

                resultado_fech = obter_resultado(concurso_fechamento)
                concurso_data_fech = resultado_fech["data"] if resultado_fech else ""

                fechamento_data = []
                for i, combo in enumerate(combos, 1):
                    combo_str = ", ".join(f"{d:02d}" for d in combo)
                    filtros = explicar_filtros(combo, concurso_fechamento)
                    dezenas_db = ",".join(str(d) for d in combo)
                    fechamento_data.append(
                        {
                            "Nº": i,
                            "Concurso": concurso_fechamento,
                            "Data": concurso_data_fech,
                            "Dezenas": combo_str,
                            "Pares": filtros["pares"],
                            "Ímpares": filtros["impares"],
                            "Primos": filtros["primos"],
                            "Moldura": filtros["moldura"],
                            "Repetidos": filtros["repetidos"] if filtros["repetidos"] is not None else "-",
                        }
                    )
                    inserir_palpite(concurso_fechamento, dezenas_db, concurso_data_fech)

                df_fechamento = pd.DataFrame(fechamento_data)
                st.dataframe(df_fechamento, hide_index=True, width='stretch')

                csv_f = df_fechamento.to_csv(index=False)
                st.download_button(
                    "📥 Baixar CSV do Fechamento",
                    data=csv_f,
                    file_name=f"fechamento_concurso_{concurso_fechamento}.csv",
                    mime="text/csv",
                )

            except ValueError as e:
                st.error(f"Erro nos números informados: {e}")
            except Exception as e:
                st.error(f"Erro ao gerar fechamento: {e}")


def tab_conferidor():
    st.subheader("🔍 Conferidor de Bilhetes")
    st.markdown("Confira seus palpites salvos contra o resultado oficial de um concurso.")

    total = get_total_concursos()

    if total == 0:
        st.warning("Nenhum concurso carregado. Sincronize os dados primeiro.")
        return

    concurso = st.number_input(
        "Número do Concurso",
        min_value=1,
        max_value=max(total, 99999),
        value=total,
        step=1,
    )

    if st.button("🔎 Conferir", type="primary", width='stretch'):
        resultado = conferir_palpites(concurso)

        if resultado is None:
            st.error(f"Concurso {concurso} não encontrado no banco de dados.")
            return

        st.subheader(f"📋 Resultado do Concurso {resultado['concurso']}")
        st.write(f"**Data:** {resultado['data']}")

        dezenas_ordenadas = sorted(resultado["dezenas_sorteadas"])
        cols = st.columns(5)
        for i, d in enumerate(dezenas_ordenadas):
            with cols[i % 5]:
                st.markdown(
                    f"<div style='text-align:center;font-size:1.3rem;font-weight:bold;"
                    f"background:#e8f5e9;border-radius:8px;padding:6px;margin:2px;"
                    f"white-space:nowrap;min-width:2.4rem;display:inline-block;'>{d:02d}</div>",
                    unsafe_allow_html=True,
                )

        bilhetes = resultado["bilhetes"]
        if not bilhetes:
            st.info(f"Nenhum palpite salvo para o concurso {concurso}.")
            return

        st.subheader(f"📑 Bilhetes Conferidos ({len(bilhetes)})")

        rows = []
        for b in bilhetes:
            dezenas_str = ", ".join(f"{d:02d}" for d in b["dezenas"])
            contest_date = b.get("concurso_data", "") or resultado["data"]
            rows.append(
                {
                    "ID": b["id"],
                    "Criado em": b["data_criacao"][:19] if b["data_criacao"] else "-",
                    "Data do Concurso": contest_date,
                    "Dezenas": dezenas_str,
                    "Acertos": b["acertos"],
                }
            )

        df = pd.DataFrame(rows)

        def highlight_acertos(val):
            if val >= 14:
                return "background-color: #28a745; color: white; font-weight: bold"
            elif val >= 11:
                return "background-color: #ffc107; color: black; font-weight: bold"
            return ""

        styled = df.style.map(highlight_acertos, subset=["Acertos"])
        st.dataframe(styled, hide_index=True, width='stretch')

        acertos_list = [b["acertos"] for b in bilhetes]
        max_acertos = max(acertos_list)
        st.metric("🏆 Melhor acerto", f"{max_acertos} pontos")

        faixas = {i: acertos_list.count(i) for i in range(16)}
        faixas_filtradas = {k: v for k, v in faixas.items() if v > 0}
        if faixas_filtradas:
            faixa_df = pd.DataFrame(
                [{"Faixa": f"{k} pontos", "Qtd": v} for k, v in sorted(faixas_filtradas.items())]
            )
            st.write("**Distribuição de Acertos:**")
            st.dataframe(faixa_df, hide_index=True, width='stretch')


def tab_palpites_salvos():
    st.subheader("📋 Palpites Salvos")
    st.markdown("Visualize, filtre e gerencie todos os palpites armazenados no banco.")

    total_palpites = contar_palpites()
    if total_palpites == 0:
        st.info("Nenhum palpite salvo ainda. Use a aba **🎯 Gerador de Palpites** para criar os primeiros.")
        return

    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        st.metric("Total de Palpites", total_palpites)
    with col2:
        concurso_filtro = st.number_input(
            "Filtrar por concurso (0 = todos)",
            min_value=0,
            max_value=99999,
            value=0,
            step=1,
            key="filtro_concurso_palpites",
        )
    with col3:
        palpites_por_pagina = st.selectbox(
            "Itens por página",
            options=[20, 50, 100],
            index=1,
            key="ppp_palpites",
        )

    filtro = concurso_filtro if concurso_filtro > 0 else None
    total_filtrado = contar_palpites(filtro)
    total_paginas = max(1, (total_filtrado + palpites_por_pagina - 1) // palpites_por_pagina)

    if "pagina_palpites" not in st.session_state:
        st.session_state.pagina_palpites = 1

    if total_paginas > 1:
        pg_cols = st.columns([1, 3, 1])
        with pg_cols[0]:
            if st.button("◀ Anterior", disabled=st.session_state.pagina_palpites <= 1):
                st.session_state.pagina_palpites -= 1
                st.rerun()
        with pg_cols[1]:
            st.markdown(
                f"<div style='text-align:center;padding:6px'>Página {st.session_state.pagina_palpites} de {total_paginas}</div>",
                unsafe_allow_html=True,
            )
        with pg_cols[2]:
            if st.button("Próximo ▶", disabled=st.session_state.pagina_palpites >= total_paginas):
                st.session_state.pagina_palpites += 1
                st.rerun()

    offset = (st.session_state.pagina_palpites - 1) * palpites_por_pagina
    palpites = listar_todos_palpites(filtro, palpites_por_pagina, offset)

    rows = []
    for p in palpites:
        dezenas = [int(x) for x in p["dezenas"].split(",")]
        dezenas_str = ", ".join(f"{d:02d}" for d in dezenas)
        rows.append(
            {
                "ID": p["id"],
                "Concurso": p["concurso_alvo"],
                "Data Concurso": p["concurso_data"] or "-",
                "Dezenas": dezenas_str,
                "Criado em": p["data_criacao"][:19] if p["data_criacao"] else "-",
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, hide_index=True, width='stretch')

    csv = df.to_csv(index=False)
    st.download_button(
        "📥 Baixar CSV",
        data=csv,
        file_name="palpites_salvos.csv",
        mime="text/csv",
    )

    st.divider()
    st.subheader("🗑️ Gerenciar Palpites")

    col_del1, col_del2 = st.columns([1, 3])
    with col_del1:
        palpite_id = st.number_input("ID do palpite para excluir", min_value=1, step=1)
    with col_del2:
        if st.button("Excluir Palpite", type="secondary"):
            if deletar_palpite(palpite_id):
                st.success(f"Palpite ID {palpite_id} excluído.")
                st.rerun()
            else:
                st.error(f"Palpite ID {palpite_id} não encontrado.")

    if st.button("🗑️ Excluir Todos os Palpites", type="secondary"):
        from src.database import get_db
        with get_db() as conn:
            conn.execute("DELETE FROM palpites")
        st.success("Todos os palpites foram excluídos.")
        st.rerun()


def main():
    init_app()
    render_sidebar()

    tabs = st.tabs(["📊 Dashboard & Sincronização", "🎯 Gerador de Palpites", "🔍 Conferidor de Bilhetes", "📋 Palpites Salvos"])

    with tabs[0]:
        tab_dashboard()

    with tabs[1]:
        tab_gerador()

    with tabs[2]:
        tab_conferidor()

    with tabs[3]:
        tab_palpites_salvos()


if __name__ == "__main__":
    main()
