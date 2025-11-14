from __future__ import annotations
import os, sys
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# ---------- setup cliente (igual já vimos) ----------

def _app_base() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

env_path = _app_base() / ".env"
load_dotenv(dotenv_path=env_path, override=False)

_client: OpenAI | None = None

def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY não encontrada.\n"
                f"Procurei em: {env_path}\n"
                "Crie um arquivo .env ao lado do executável com:\n"
                "OPENAI_API_KEY=sua_chave_aqui"
            )
        _client = OpenAI(api_key=api_key)
    return _client

# ID do agente salvo
_PROMPT_ID = "pmpt_691610f1f92c8195813434067cd51f490c72f28960d54f47"

# ---------- AQUI: função para até 5 PDFs ----------

def analisar_pdfs(caminhos_pdfs: list[Path]) -> str:
    """
    Envia até 5 PDFs para o agente e retorna uma única resposta.
    """
    if not caminhos_pdfs:
        return "Erro: nenhum PDF informado."

    # garante no máximo 5
    caminhos_pdfs = caminhos_pdfs[:5]

    # valida arquivos
    pdfs_validos: list[Path] = []
    for p in caminhos_pdfs:
        if not p.exists() or not p.is_file():
            return f"Erro: arquivo não encontrado: {p}"
        if p.suffix.lower() != ".pdf":
            return f"Erro: arquivo não é PDF: {p}"
        pdfs_validos.append(p)

    client = _get_client()

    file_ids: list[str] = []
    try:
        # 1) faz upload de todos os PDFs
        for p in pdfs_validos:
            with open(p, "rb") as f:
                uploaded = client.files.create(file=f, purpose="assistants")
            file_ids.append(uploaded.id)

        # 2) monta o conteúdo da mensagem pro agente
        conteudo = []
           

        # adiciona cada PDF como input_file
        for fid in file_ids:
            conteudo.append({"type": "input_file", "file_id": fid})

        # 3) chama o agente salvo
        response = client.responses.create(
            prompt={"id": _PROMPT_ID},
            input=[
                {
                    "role": "user",
                    "content": conteudo,
                }
            ],
        )

        saida = (response.output_text or "").strip()
        return saida or "(Sem conteúdo retornado pelo agente.)"

    except Exception as exc:
        return f"Erro ao consultar a IA: {exc!s}"

    finally:
        # 4) tenta deletar os arquivos enviados (boa prática)
        try:
            if file_ids:
                for fid in file_ids:
                    try:
                        client.files.delete(fid)
                    except Exception:
                        pass
        except Exception:
            pass

if __name__ == "__main__":
    # exemplo com 2 PDFs
    pdfs = [
        Path("05. CAT - 12.06.2019 - Trajeto.pdf"),
        Path("06. Laudo Médico - Pericial.pdf"),
        Path("07. Decl. de Benefício.pdf"),
        Path("09.1. DECLARAÇÃO + PROCURAÇÃO - ASSINADOS!.pdf"),
        Path("Roteiro de Visita.pdf"),
    ]
    print("✅ Enviando PDFs:", pdfs)
    texto = analisar_pdfs(pdfs)
    print("\n📄 Resultado da análise:\n")
    print(texto)