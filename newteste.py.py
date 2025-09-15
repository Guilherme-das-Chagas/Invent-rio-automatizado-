import pandas as pd
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import os

# Caminho da planilha e do log
arquivo = "Book 1.xlsx"
logfile = "inventario_log.txt"

# Função para registrar movimentação (entrada ou saída)
def registrar_movimento(tipo):
    produto = entrada_produto.get().strip()
    qtd_movimento = entrada_quantidade.get().strip()

    if not produto or not qtd_movimento:
        messagebox.showerror("Erro", "Preencha todos os campos!")
        return
    
    try:
        qtd_movimento = int(qtd_movimento)
    except ValueError:
        messagebox.showerror("Erro", "Quantidade deve ser um número inteiro!")
        return

    if not os.path.exists(arquivo):
        messagebox.showerror("Erro", f"Arquivo '{arquivo}' não encontrado!")
        return

    # Ler planilha
    df = pd.read_excel(arquivo, sheet_name="Planilha1")
    df.columns = df.columns.str.strip()

    # Renomear colunas para facilitar
    df = df.rename(columns={
        "Especificação/Hardware": "Produto",
        "Localiza/Armario": "Local",
        "Quantidade": "Quantidade"
    })

    # Verifica se o produto existe
    if produto not in df["Produto"].values:
        messagebox.showerror("Erro", f"O produto '{produto}' não foi encontrado!")
        return

    # Atualiza quantidade de acordo com o tipo
    idx = df[df["Produto"] == produto].index[0]
    qtd_atual = int(df.at[idx, "Quantidade"])

    if tipo == "saida":
        if qtd_atual < qtd_movimento:
            messagebox.showerror("Erro", f"Estoque insuficiente para saída de {qtd_movimento} unidades!")
            return
        qtd_final = qtd_atual - qtd_movimento
        movimento = f"Saída de {qtd_movimento} unidade(s)"
    elif tipo == "entrada":
        qtd_final = qtd_atual + qtd_movimento
        movimento = f"Entrada de {qtd_movimento} unidade(s)"

    # Atualiza planilha
    df.at[idx, "Quantidade"] = int(qtd_final)
    df.at[idx, "Data Atualização"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Salva na planilha
    df["Quantidade"] = df["Quantidade"].fillna(0).astype(int)
    df.to_excel(arquivo, sheet_name="Planilha1", index=False)

    # Salva no log com status completo
    with open(logfile, "a", encoding="utf-8") as f:
        f.write(
            f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {movimento} no produto '{produto}' | "
            f"Quantidade antes: {qtd_atual} | Movimentado: {qtd_movimento} | Quantidade final: {qtd_final}\n"
        )

    messagebox.showinfo("Sucesso", f"{movimento} registrada para '{produto}'")

    entrada_produto.delete(0, tk.END)
    entrada_quantidade.delete(0, tk.END)

# Interface gráfica
janela = tk.Tk()
janela.title("Controle de Inventário")

tk.Label(janela, text="Produto:").grid(row=0, column=0, padx=10, pady=10)
entrada_produto = tk.Entry(janela)
entrada_produto.grid(row=0, column=1, padx=10, pady=10)

tk.Label(janela, text="Quantidade:").grid(row=1, column=0, padx=10, pady=10)
entrada_quantidade = tk.Entry(janela)
entrada_quantidade.grid(row=1, column=1, padx=10, pady=10)

botao_saida = tk.Button(janela, text="Registrar Saída", bg="red", fg="white", command=lambda: registrar_movimento("saida"))
botao_saida.grid(row=2, column=0, padx=10, pady=20)

botao_entrada = tk.Button(janela, text="Registrar Entrada", bg="green", fg="white", command=lambda: registrar_movimento("entrada"))
botao_entrada.grid(row=2, column=1, padx=10, pady=20)

janela.mainloop()
