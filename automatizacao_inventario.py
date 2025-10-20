# Tooltip customizado para Tkinter
class ToolTip(object):
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)

    def show_tip(self, event=None):
        if self.tipwindow or not self.text:
            return
        # Correção aqui:
        cx, cy = 0, 0
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 20
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw, text=self.text, justify='left', background="#ffffe0",
            relief='solid', borderwidth=1, font=("tahoma", "9", "normal")
        )
        label.pack(ipadx=1)

    def hide_tip(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()


# Imports necessários
import tkinter as tk
from tkinter import messagebox, filedialog
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.drawing.image import Image as XLImage
import os
import pandas as pd
from datetime import datetime
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Caminho do log
logfile = "inventario_log.txt"
arquivo = ""

# Mapeamento de possíveis nomes de colunas
colunas_possiveis = {
    "Produto": ["Produto", "Item", "Nome", "Hardware", "Especificação/Hardware"],
    "Quantidade": ["Quantidade", "Qtd", "Estoque", "Qtde"]
}

# Função para encontrar o nome real da coluna
def encontrar_coluna(df, tipo):
    for nome in colunas_possiveis[tipo]:
        if nome in df.columns:
            return nome
    return None

# Seleciona o arquivo Excel
def selecionar_arquivo():
    global arquivo
    arquivo = filedialog.askopenfilename(
        title="Selecione a planilha de inventário",
        filetypes=[("Planilhas Excel", "*.xlsx *.xls")]
    )
    if not arquivo:
        messagebox.showerror("Erro", "Nenhum arquivo selecionado. O sistema será encerrado.")
        janela.destroy()
    else:
        carregar_hardware()

# Carrega lista de produtos da planilha
def carregar_hardware():
    try:
        df_temp = pd.read_excel(arquivo)
        df_temp.columns = df_temp.columns.str.strip()

        col_produto = encontrar_coluna(df_temp, "Produto")
        if not col_produto:
            messagebox.showerror("Erro", "A planilha precisa conter uma coluna de produtos.")
            janela.destroy()
            return

        lista = df_temp[col_produto].dropna().unique().tolist()
        # Separe ativos e periféricos
        ativos = [item for item in lista if "notebook" in str(item).lower()]
        perifericos = [item for item in lista if "notebook" not in str(item).lower()]

        listbox_perifericos.delete(0, tk.END)
        for item in perifericos:
            listbox_perifericos.insert(tk.END, item)

        listbox_ativos.delete(0, tk.END)
        for item in ativos:
            listbox_ativos.insert(tk.END, item)

        atualizar_relatorio()
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao carregar a planilha: {e}")
        janela.destroy()

# Função para exportar gráfico real do inventário
def exportar_grafico_excel():
    if not arquivo:
        messagebox.showerror('Erro', 'Nenhum arquivo de inventário carregado!')
        return
    try:
        import re
        import numpy as np
        # 1. Lê o log de movimentações
        entradas = {}
        saidas = {}
        datas = set()
        with open(logfile, 'r', encoding='utf-8') as f:
            for linha in f:
                m = re.match(r'\[(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (Entrada|Saída) de (\d+) no produto', linha)
                if m:
                    data = m.group(1)
                    tipo = m.group(3)
                    qtd = int(m.group(4))
                    datas.add(data)
                    if tipo == 'Entrada':
                        entradas[data] = entradas.get(data, 0) + qtd
                    else:
                        saidas[data] = saidas.get(data, 0) + qtd
        datas = sorted(list(datas), key=lambda d: datetime.strptime(d, '%d/%m/%Y'))
        # 2. Estoque final do dia (soma de todos os produtos)
        df = pd.read_excel(arquivo)
        df.columns = df.columns.str.strip()
        col_qtd = encontrar_coluna(df, "Quantidade")
        estoque_total = df[col_qtd].fillna(0).astype(int).sum() if col_qtd else 0
        estoque = []
        # Para cada data, simula o estoque final daquele dia
        estoque_sim = 0
        estoque_por_dia = {}
        # Reprocessa o log para simular o estoque ao longo dos dias
        movimentos = []
        with open(logfile, 'r', encoding='utf-8') as f:
            for linha in f:
                m = re.match(r'\[(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (Entrada|Saída) de (\d+) no produto', linha)
                if m:
                    data = m.group(1)
                    tipo = m.group(3)
                    qtd = int(m.group(4))
                    movimentos.append((data, tipo, qtd))
        # Ordena por data
        movimentos.sort(key=lambda x: datetime.strptime(x[0], '%d/%m/%Y'))
        estoque_atual = 0
        estoque_por_dia = {}
        for data in datas:
            # Soma todos os movimentos até o final do dia
            entradas_dia = sum(q for d, t, q in movimentos if d == data and t == 'Entrada')
            saidas_dia = sum(q for d, t, q in movimentos if d == data and t == 'Saída')
            estoque_atual += entradas_dia - saidas_dia
            estoque_por_dia[data] = estoque_atual
        # Se não houver movimentação, usa o estoque atual
        if not estoque_por_dia and estoque_total:
            estoque_por_dia[datas[-1]] = estoque_total
        # 3. Monta DataFrame para plotar
        df_plot = pd.DataFrame({
            'Entradas': [entradas.get(d, 0) for d in datas],
            'Saídas': [saidas.get(d, 0) for d in datas],
            'Estoque': [estoque_por_dia.get(d, np.nan) for d in datas]
        }, index=datas)

        # 4. Gera gráficos separados
        # Gráfico 1: Entradas
        fig1, ax1 = plt.subplots(figsize=(8, 4))
        df_plot['Entradas'].plot(kind='bar', ax=ax1, color='green')
        ax1.set_ylabel('Entradas')
        ax1.set_xlabel('Data')
        ax1.set_title('Entradas por Data')
        plt.tight_layout()
        grafico_entradas = 'grafico_entradas.png'
        fig1.savefig(grafico_entradas)
        plt.close(fig1)

        # Gráfico 2: Saídas
        fig2, ax2 = plt.subplots(figsize=(8, 4))
        df_plot['Saídas'].plot(kind='bar', ax=ax2, color='red')
        ax2.set_ylabel('Saídas')
        ax2.set_xlabel('Data')
        ax2.set_title('Saídas por Data')
        plt.tight_layout()
        grafico_saidas = 'grafico_saidas.png'
        fig2.savefig(grafico_saidas)
        plt.close(fig2)

        # Gráfico 3: Estoque
        fig3, ax3 = plt.subplots(figsize=(8, 4))
        df_plot['Estoque'].plot(ax=ax3, color='black', marker='o', linewidth=2)
        ax3.set_ylabel('Estoque')
        ax3.set_xlabel('Data')
        ax3.set_title('Estoque ao Longo do Tempo')
        plt.tight_layout()
        grafico_estoque = 'grafico_estoque.png'
        fig3.savefig(grafico_estoque)
        plt.close(fig3)

        # Cria planilha Excel e insere as imagens
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Gráficos'
        img1 = XLImage(grafico_entradas)
        img2 = XLImage(grafico_saidas)
        img3 = XLImage(grafico_estoque)
        ws.add_image(img1, 'A1')
        ws.add_image(img2, 'A25')
        ws.add_image(img3, 'A49')
        excel_path = 'grafico_exportado.xlsx'
        wb.save(excel_path)
        # Remove imagens temporárias
        os.remove(grafico_entradas)
        os.remove(grafico_saidas)
        os.remove(grafico_estoque)
        messagebox.showinfo('Exportação', f'Gráficos exportados para {excel_path}')
    except Exception as e:
        messagebox.showerror('Erro', f'Erro ao exportar gráfico: {e}')

def abrir_graficos():
    import matplotlib.pyplot as plt
    import pandas as pd
    import re
    import openpyxl
    from openpyxl.drawing.image import Image as XLImage
    import numpy as np

    movimentos = []
    if not os.path.exists(logfile):
        messagebox.showinfo("Info", "Nenhuma movimentação registrada ainda.")
        return

    with open(logfile, 'r', encoding='utf-8') as f:
        for linha in f:
            m = re.match(r'\[(\d{2}/\d{2}/\d{4}) (\d{2}:\d{2}:\d{2})\] (Entrada|Saída) de (\d+) no produto \'([^\']+)\'', linha)
            if m:
                data = m.group(1)
                tipo = m.group(3)
                qtd = int(m.group(4))
                produto = m.group(5)
                movimentos.append({'data': data, 'tipo': tipo, 'qtd': qtd, 'produto': produto})

    if not movimentos:
        messagebox.showinfo("Info", "Nenhuma movimentação registrada ainda.")
        return

    df_mov = pd.DataFrame(movimentos)
    df_mov['data'] = pd.to_datetime(df_mov['data'], format='%d/%m/%Y')

    filtro = tk.Toplevel(janela)
    filtro.title("Gráficos e Filtros")
    filtro.geometry("540x480")
    filtro.configure(bg=cor_fundo)

    tk.Label(filtro, text="Tipo de movimentação:", bg=cor_fundo).pack()
    tipo_var = tk.StringVar(value="Saída")
    tk.OptionMenu(filtro, tipo_var, "Saída", "Entrada", "Ambos").pack()

    tk.Label(filtro, text="Categoria:", bg=cor_fundo).pack()
    categoria_var = tk.StringVar(value="Ambos")
    op_menu = tk.OptionMenu(filtro, categoria_var, "Ativos", "Periféricos", "Ambos")
    op_menu.pack()

    tk.Label(filtro, text="Tipo de Gráfico:", bg=cor_fundo).pack()
    grafico_var = tk.StringVar(value="Barras")
    tk.OptionMenu(filtro, grafico_var, "Barras", "Pizza", "Pirâmide").pack()

    tk.Label(filtro, text="Elementos na categoria:", bg=cor_fundo).pack()
    produtos_text = tk.Text(filtro, height=4, width=55, bg="#f7fbff", state='disabled')
    produtos_text.pack(pady=(0, 8))

    def filtrar_categoria(df):
        cat = categoria_var.get()
        if cat == "Ambos":
            return df
        elif cat == "Ativos":
            return df[df['produto'].str.lower().str.contains("notebook")]
        else:
            return df[~df['produto'].str.lower().str.contains("notebook")]

    def atualizar_produtos_categoria(*args):
        produtos_text.config(state='normal')
        produtos_text.delete(1.0, tk.END)
        df_filtrado = filtrar_categoria(df_mov)
        produtos = sorted(df_filtrado['produto'].unique())
        if produtos:
            produtos_text.insert(tk.END, ", ".join(produtos))
        else:
            produtos_text.insert(tk.END, "Nenhum elemento encontrado.")
        produtos_text.config(state='disabled')

    categoria_var.trace_add('write', lambda *args: atualizar_produtos_categoria())
    atualizar_produtos_categoria()

    tk.Label(filtro, text="Produto (deixe em branco para todos):", bg=cor_fundo).pack()
    produto_var = tk.StringVar()
    tk.Entry(filtro, textvariable=produto_var).pack()

    tk.Label(filtro, text="Período (dd/mm/aaaa - dd/mm/aaaa):", bg=cor_fundo).pack()
    periodo_var = tk.StringVar()
    tk.Entry(filtro, textvariable=periodo_var).pack()

    def gerar_grafico(exportar_excel=False):
        tipo = tipo_var.get()
        produto = produto_var.get().strip()
        periodo = periodo_var.get().strip()
        tipo_grafico = grafico_var.get()

        df_filtro = df_mov.copy()
        df_filtro = filtrar_categoria(df_filtro)
        if tipo != "Ambos":
            df_filtro = df_filtro[df_filtro['tipo'] == tipo]
        if produto:
            df_filtro = df_filtro[df_filtro['produto'].str.contains(produto, case=False, na=False)]
        if periodo:
            try:
                ini, fim = [x.strip() for x in periodo.split('-')]
                ini = pd.to_datetime(ini, format='%d/%m/%Y')
                fim = pd.to_datetime(fim, format='%d/%m/%Y')
                df_filtro = df_filtro[(df_filtro['data'] >= ini) & (df_filtro['data'] <= fim)]
            except Exception:
                messagebox.showerror("Erro", "Período inválido. Use o formato dd/mm/aaaa - dd/mm/aaaa.")
                return

        if df_filtro.empty:
            messagebox.showinfo("Info", "Nenhum dado para o filtro selecionado.")
            return

        resumo = df_filtro.groupby('produto')['qtd'].sum().sort_values(ascending=False)
        resumo = resumo.astype(int)  # Garante números inteiros

        colors = plt.cm.Paired(range(len(resumo)))

        fig, ax = plt.subplots(figsize=(8, 5))
        img_path = None

        if tipo_grafico == "Pizza":
            def make_autopct(values):
                def my_autopct(pct):
                    total = sum(values)
                    val = int(round(pct*total/100.0))
                    return f'{val:d}'
                return my_autopct
            wedges, texts, autotexts = ax.pie(
                resumo, labels=resumo.index, autopct=make_autopct(resumo.values),
                startangle=140, colors=colors, textprops={'fontsize': 10}
            )
            for autotext in autotexts:
                autotext.set_color('black')
            ax.set_title(f"Distribuição de {tipo.lower()}s por produto ({categoria_var.get()})", fontsize=13)
            plt.tight_layout()
            img_path = "grafico_pizza.png"
        elif tipo_grafico == "Pirâmide":
            resumo[::-1].plot(kind='barh', color='skyblue', ax=ax)
            for y, valor in zip(ax.patches, resumo[::-1]):
                ax.text(y.get_width()+0.1, y.get_y()+y.get_height()/2, f'{int(valor)}', va='center', fontsize=10)
            ax.set_title(f"Pirâmide de {tipo.lower()}s por produto ({categoria_var.get()})", fontsize=13)
            ax.set_xlabel("Quantidade")
            ax.set_ylabel("Produto")
            plt.tight_layout()
            img_path = "grafico_piramide.png"
        else:  # Barras verticais
            resumo.plot(kind='bar', color='dodgerblue', ax=ax)
            for i, valor in enumerate(resumo):
                ax.text(i, valor+0.1, f'{int(valor)}', ha='center', va='bottom', fontsize=10)
            ax.set_title(f"Barras de {tipo.lower()}s por produto ({categoria_var.get()})", fontsize=13)
            ax.set_xlabel("Produto")
            ax.set_ylabel("Quantidade")
            plt.tight_layout()
            img_path = "grafico_barras.png"

        if exportar_excel:
            fig.savefig(img_path)
            plt.close(fig)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = 'Gráfico'
            img = XLImage(img_path)
            ws.add_image(img, 'A1')
            excel_path = 'grafico_exportado.xlsx'
            wb.save(excel_path)
            os.remove(img_path)
            messagebox.showinfo('Exportação', f'Gráfico exportado para {excel_path}')
        else:
            plt.show()

    tk.Button(filtro, text="Gerar Gráfico", command=lambda: gerar_grafico(False), bg="orange").pack(pady=10)
    tk.Button(filtro, text="Exportar Gráfico para Excel", command=lambda: gerar_grafico(True), bg="#0077cc", fg="white").pack(pady=5)

# Registrar movimentação
def registrar_movimento(tipo):
    selecionados = listbox_hardware.curselection()
    qtd_movimento = entrada_quantidade.get().strip()
    descricao = entrada_descricao.get().strip()
    ticket = entrada_ticket.get().strip()  # <-- Novo campo

    selecionados_perif = listbox_perifericos.curselection()
    selecionados_ativos = listbox_ativos.curselection()

    if (not selecionados_perif and not selecionados_ativos) or not qtd_movimento:
        messagebox.showerror("Erro", "Selecione pelo menos um periférico ou ativo e informe a quantidade!")
        return

    try:
        qtd_movimento = int(qtd_movimento)
    except ValueError:
        messagebox.showerror("Erro", "Quantidade deve ser um número inteiro!")
        return

    df = pd.read_excel(arquivo)
    df.columns = df.columns.str.strip()

    col_produto = encontrar_coluna(df, "Produto")
    col_qtd = encontrar_coluna(df, "Quantidade")

    if not col_produto or not col_qtd:
        messagebox.showerror("Erro", "A planilha precisa conter colunas de produto e quantidade.")
        return

    lista_hardware = listbox_hardware.get(0, tk.END)
    resultado = []
    # Periféricos
    lista_perifericos = listbox_perifericos.get(0, tk.END)
    for i in selecionados_perif:
        produto = lista_perifericos[i]
        if produto not in df[col_produto].values:
            resultado.append(f"❌ '{produto}' não encontrado.")
            continue

        idx = df[df[col_produto] == produto].index[0]
        qtd_atual = int(df.at[idx, col_qtd])

        if tipo == "saida":
            if qtd_atual < qtd_movimento:
                resultado.append(f"⚠️ Estoque insuficiente para '{produto}' (Atual: {qtd_atual})")
                continue
            qtd_final = qtd_atual - qtd_movimento
            movimento = f"Saída de {qtd_movimento}"
        else:
            qtd_final = qtd_atual + qtd_movimento
            movimento = f"Entrada de {qtd_movimento}"

        df.at[idx, col_qtd] = qtd_final
        df.at[idx, "Data Atualização"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # Inclui o ticket no log, se informado
        ticket_str = f" | Ticket: {ticket}" if ticket else ""
        with open(logfile, "a", encoding="utf-8") as f:
            f.write(
                f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {movimento} no produto '{produto}' | "
                f"Antes: {qtd_atual} | Movimentado: {qtd_movimento} | Final: {qtd_final} | Motivo: {descricao}{ticket_str}\n"
            )

        resultado.append(f"✅ {movimento} registrada para '{produto}'")

    df[col_qtd] = df[col_qtd].fillna(0).astype(int)
    df.to_excel(arquivo, index=False)

    messagebox.showinfo("Resultado", "\n".join(resultado))
    entrada_quantidade.delete(0, tk.END)
    entrada_descricao.delete(0, tk.END)
    entrada_ticket.delete(0, tk.END)  # Limpa o campo ticket
    atualizar_relatorio()

# Atualiza relatório
def atualizar_relatorio():
    texto_perifericos.delete(1.0, tk.END)
    texto_ativos.delete(1.0, tk.END)
    try:
        df = pd.read_excel(arquivo)
        df.columns = df.columns.str.strip()

        col_produto = encontrar_coluna(df, "Produto")
        col_qtd = encontrar_coluna(df, "Quantidade")

        if not col_produto or not col_qtd:
            texto_perifericos.insert(tk.END, "Colunas de produto e quantidade não encontradas.")
            texto_ativos.insert(tk.END, "Colunas de produto e quantidade não encontradas.")
            return

        relatorio = df.groupby(col_produto)[col_qtd].sum().sort_values(ascending=False)
        # Filtro: ativos = contém "notebook" (pode ajustar para outros ativos)
        ativos = {prod: qtd for prod, qtd in relatorio.items() if "notebook" in prod.lower()}
        perifericos = {prod: qtd for prod, qtd in relatorio.items() if "notebook" not in prod.lower()}

        texto_perifericos.insert(tk.END, "📦 Periféricos:\n\n")
        for produto, total in perifericos.items():
            texto_perifericos.insert(tk.END, f"{produto}: {total} unidade(s)\n")

        texto_ativos.insert(tk.END, "💻 Ativos:\n\n")
        for produto, total in ativos.items():
            texto_ativos.insert(tk.END, f"{produto}: {total} unidade(s)\n")
    except Exception as e:
        texto_perifericos.insert(tk.END, f"Erro ao gerar relatório: {e}")
        texto_ativos.insert(tk.END, f"Erro ao gerar relatório: {e}")


def atualizar_grafico_estoque():
    global canvas_estoque
    # Remove gráfico antigo se existir
    if canvas_estoque is not None:
        canvas_estoque.get_tk_widget().destroy()
        canvas_estoque = None

    try:
        df = pd.read_excel(arquivo)
        df.columns = df.columns.str.strip()
        col_produto = encontrar_coluna(df, "Produto")
        col_qtd = encontrar_coluna(df, "Quantidade")
        if not col_produto or not col_qtd:
            return

        relatorio = df.groupby(col_produto)[col_qtd].sum().sort_values(ascending=False)
        produtos = list(relatorio.index)
        quantidades = list(relatorio.values)

        fig, ax = plt.subplots(figsize=(6, 2.8))
        bars = ax.bar(produtos, quantidades, color='dodgerblue')
        ax.set_ylabel('Quantidade')
        ax.set_title('Estoque Atual por Produto')
        ax.set_xticklabels(produtos, rotation=45, ha='right', fontsize=9)
        # Adiciona os valores inteiros acima das barras
        for bar, qtd in zip(bars, quantidades):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.1, f'{int(qtd)}', ha='center', va='bottom', fontsize=9)
        fig.tight_layout()
        canvas_estoque = FigureCanvasTkAgg(fig, master=frame_grafico_estoque)
        canvas_estoque.draw()
        canvas_estoque.get_tk_widget().pack()
        plt.close(fig)
    except Exception:
        pass

# Interface gráfica

cor_fundo = '#e3f0ff'      # azul claro agradável
cor_label = '#d0e6fa'      # azul ainda mais claro para labels
cor_box = '#f7fbff'        # branco azulado para caixas
cor_borda = '#b3d1f7'      # azul para bordas

janela = tk.Tk()
janela.title("Controle de Inventário")
janela.geometry("1000x650")
janela.configure(bg=cor_fundo)

# Painel principal dividido em dois frames (esquerda e direita)
frame_principal = tk.Frame(janela, bg=cor_fundo)
frame_principal.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

frame_esq = tk.Frame(frame_principal, bg=cor_fundo)
frame_esq.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20), pady=10)

frame_dir = tk.Frame(frame_principal, bg=cor_fundo)
frame_dir.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, pady=10)

# --- Painel Esquerdo: Entradas e seleção ---

# --- Seleção de Periféricos (agora no topo) ---
frame_perif = tk.Frame(frame_esq, bg=cor_fundo)
frame_perif.pack(pady=8, anchor='w')
tk.Label(frame_perif, text="Selecione Periféricos:", bg=cor_label, width=25, anchor='w').pack(side=tk.LEFT)
btn_perif = tk.Label(frame_perif, text="❓", bg=cor_fundo, fg="#0077cc", cursor="question_arrow")
btn_perif.pack(side=tk.LEFT, padx=5)
ToolTip(btn_perif, "Selecione um ou mais periféricos para movimentação de estoque.")

listbox_perifericos = tk.Listbox(frame_esq, selectmode=tk.MULTIPLE, height=6, width=35, bg=cor_box, highlightbackground=cor_borda)
listbox_perifericos.pack(pady=2, anchor='w')

# --- Seleção de Ativos (logo abaixo dos periféricos) ---
frame_ativos_sel = tk.Frame(frame_esq, bg=cor_fundo)
frame_ativos_sel.pack(pady=8, anchor='w')
tk.Label(frame_ativos_sel, text="Selecione Ativos:", bg=cor_label, width=25, anchor='w').pack(side=tk.LEFT)
btn_ativos_sel = tk.Label(frame_ativos_sel, text="❓", bg=cor_fundo, fg="#0077cc", cursor="question_arrow")
btn_ativos_sel.pack(side=tk.LEFT, padx=5)
ToolTip(btn_ativos_sel, "Selecione um ou mais ativos (ex: notebooks) para movimentação de estoque.")

listbox_ativos = tk.Listbox(frame_esq, selectmode=tk.MULTIPLE, height=4, width=35, bg=cor_box, highlightbackground=cor_borda)
listbox_ativos.pack(pady=2, anchor='w')

# Campo Quantidade
frame_qtd = tk.Frame(frame_esq, bg=cor_fundo)
frame_qtd.pack(pady=8, anchor='w')
tk.Label(frame_qtd, text="Quantidade:", bg=cor_label, width=25, anchor='w').pack(side=tk.LEFT)
btn_qtd = tk.Label(frame_qtd, text="❓", bg=cor_fundo, fg="#0077cc", cursor="question_arrow")
btn_qtd.pack(side=tk.LEFT, padx=5)
ToolTip(btn_qtd, "Informe a quantidade a ser movimentada (entrada ou saída).")
entrada_quantidade = tk.Entry(frame_esq, width=15, bg='white')
entrada_quantidade.pack(anchor='w')

# Campo Motivo
frame_motivo = tk.Frame(frame_esq, bg=cor_fundo)
frame_motivo.pack(pady=8, anchor='w')
tk.Label(frame_motivo, text="Motivo da movimentação:", bg=cor_label, width=25, anchor='w').pack(side=tk.LEFT)
btn_motivo = tk.Label(frame_motivo, text="❓", bg=cor_fundo, fg="#0077cc", cursor="question_arrow")
btn_motivo.pack(side=tk.LEFT, padx=5)
ToolTip(btn_motivo, "Descreva o motivo da movimentação para controle no histórico.")
entrada_descricao = tk.Entry(frame_esq, width=35, bg='white')
entrada_descricao.pack(anchor='w')

# Campo Ticket (opcional)
frame_ticket = tk.Frame(frame_esq, bg=cor_fundo)
frame_ticket.pack(pady=8, anchor='w')
tk.Label(frame_ticket, text="Ticket (opcional):", bg=cor_label, width=25, anchor='w').pack(side=tk.LEFT)
btn_ticket = tk.Label(frame_ticket, text="❓", bg=cor_fundo, fg="#0077cc", cursor="question_arrow")
btn_ticket.pack(side=tk.LEFT, padx=5)
ToolTip(btn_ticket, "Informe o número do ticket relacionado, se houver.")
entrada_ticket = tk.Entry(frame_esq, width=20, bg='white')
entrada_ticket.pack(anchor='w')

# Botões principais
frame_botoes = tk.Frame(frame_esq, bg=cor_fundo)
frame_botoes.pack(pady=18, anchor='w')
tk.Button(frame_botoes, text="Registrar Saída", bg="red", fg="white", width=15, command=lambda: registrar_movimento("saida")).grid(row=0, column=0, padx=5)
tk.Button(frame_botoes, text="Registrar Entrada", bg="green", fg="white", width=15, command=lambda: registrar_movimento("entrada")).grid(row=0, column=1, padx=5)
tk.Button(frame_botoes, text="Atualizar Relatório", bg="blue", fg="white", width=18, command=atualizar_relatorio).grid(row=1, column=0, padx=5, pady=5)
tk.Button(frame_botoes, text="Gráficos e Filtros", bg="#0077cc", fg="white", width=18, command=abrir_graficos).grid(row=1, column=1, padx=5, pady=5)

# --- Painel Direito: Relatório e Gestão de Ativos ---

# Frame para dividir lado a lado
frame_relatorios = tk.Frame(frame_dir, bg=cor_fundo)
frame_relatorios.pack(pady=8, fill=tk.X)

# Ambos os quadros com o mesmo tamanho e alinhamento
frame_ativos_rel = tk.Frame(frame_relatorios, bg=cor_fundo)
frame_ativos_rel.pack(side=tk.LEFT, padx=10, anchor='n')

tk.Label(frame_ativos_rel, text="Estoque de Ativos:", bg=cor_label, font=("Arial", 11, "bold")).pack(pady=(2,2), anchor='n')
texto_ativos = tk.Text(frame_ativos_rel, height=22, width=65, bg=cor_box, highlightbackground=cor_borda)
texto_ativos.pack(pady=(0,8), anchor='n')

frame_perif_rel = tk.Frame(frame_relatorios, bg=cor_fundo)
frame_perif_rel.pack(side=tk.LEFT, padx=10, anchor='n')

tk.Label(frame_perif_rel, text="Estoque de Periféricos:", bg=cor_label, font=("Arial", 11, "bold")).pack(pady=(2,2), anchor='n')
# Aumente apenas o quadro de periféricos
texto_perifericos = tk.Text(frame_perif_rel, height=22, width=65, bg=cor_box, highlightbackground=cor_borda)
texto_perifericos.pack(pady=(0,8), anchor='n')

# Gráfico de barras do estoque atual
frame_grafico_estoque = tk.Frame(frame_dir, bg=cor_fundo)
frame_grafico_estoque.pack(pady=10, fill=tk.BOTH, expand=False)
canvas_estoque = None

# --- Gestão de Ativos ---
frame_ativos = tk.LabelFrame(frame_dir, text="Gestão de Ativos (Notebooks)", bg=cor_fundo, fg="#003366", font=("Arial", 11, "bold"))
frame_ativos.pack(pady=10, fill=tk.X, padx=10, anchor='n')

tk.Label(frame_ativos, text="Marca do Notebook:", bg=cor_fundo, anchor='w').grid(row=0, column=0, sticky='w', padx=5, pady=2)
entrada_marca = tk.Entry(frame_ativos, width=22, bg='white')
entrada_marca.grid(row=0, column=1, padx=5, pady=2)

tk.Label(frame_ativos, text="BP:", bg=cor_fundo, anchor='w').grid(row=1, column=0, sticky='w', padx=5, pady=2)
entrada_bp = tk.Entry(frame_ativos, width=22, bg='white')
entrada_bp.grid(row=1, column=1, padx=5, pady=2)

tk.Label(frame_ativos, text="Número Serial:", bg=cor_fundo, anchor='w').grid(row=2, column=0, sticky='w', padx=5, pady=2)
entrada_serial = tk.Entry(frame_ativos, width=22, bg='white')
entrada_serial.grid(row=2, column=1, padx=5, pady=2)

def registrar_ativo():
    marca = entrada_marca.get().strip()
    bp = entrada_bp.get().strip()
    serial = entrada_serial.get().strip()
    if not marca or not bp or not serial:
        messagebox.showwarning("Atenção", "Preencha todos os campos do ativo!")
        return
    with open("ativos_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} | Marca: {marca} | BP: {bp} | Serial: {serial}\n")
    messagebox.showinfo("Gestão de Ativos", "Ativo registrado com sucesso!")
    entrada_marca.delete(0, tk.END)
    entrada_bp.delete(0, tk.END)
    entrada_serial.delete(0, tk.END)

tk.Button(frame_ativos, text="Registrar Ativo", bg="#0077cc", fg="white", command=registrar_ativo).grid(row=3, column=0, columnspan=2, pady=8)

janela.after(100, selecionar_arquivo)
janela.mainloop()



