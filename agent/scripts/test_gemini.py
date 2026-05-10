"""One-shot empirical test of Gemini API for our use cases.

Validates:
1. API key works (basic call)
2. Gemini-as-Fetcher with Google Search grounding (find recent cardio articles)
3. Gemini YouTube URL analysis (extract transcript + analyze content)

Run via GitHub Actions workflow_dispatch. Reads GOOGLE_API_KEY from env.
Prints structured results so we can evaluate quality before committing
to full integration.
"""
import os
import sys
import json
from datetime import datetime, timedelta, timezone


def main():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set in environment")
        sys.exit(1)

    print("=" * 70)
    print("GEMINI API EMPIRICAL TEST")
    print("=" * 70)
    print(f"API key found: {api_key[:8]}... (length {len(api_key)})")
    print()

    try:
        from google import genai
        from google.genai import types
        print("✓ google-genai SDK imported OK")
    except ImportError as e:
        print(f"ERROR: google-genai SDK not installed: {e}")
        sys.exit(1)

    client = genai.Client(api_key=api_key)
    print("✓ Gemini client initialized")
    print()

    # ============================================================
    # TEST 1: Basic connectivity (gemini-2.5-flash, simple prompt)
    # ============================================================
    print("─" * 70)
    print("TEST 1: Basic connectivity (gemini-2.5-flash)")
    print("─" * 70)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Em 1 frase em português: o que é fibrilação atrial?",
        )
        text = response.text.strip()
        print(f"✓ Response received ({len(text)} chars):")
        print(f"  {text}")
        print()
    except Exception as e:
        print(f"✗ TEST 1 FAILED: {e}")
        sys.exit(1)

    # ============================================================
    # TEST 2: Gemini-as-Fetcher with Google Search grounding
    # Use case: list recent cardio articles from journal websites
    # ============================================================
    print("─" * 70)
    print("TEST 2: Gemini-as-Fetcher with grounding (gemini-2.5-flash — free tier)")
    print("─" * 70)

    # Window: yesterday (Brasilia)
    brasilia_tz = timezone(timedelta(hours=-3))
    yesterday = (datetime.now(brasilia_tz) - timedelta(days=1)).strftime("%Y-%m-%d")
    today_str = datetime.now(brasilia_tz).strftime("%Y-%m-%d")

    fetcher_prompt = f"""Você é um agregador de URLs. Liste artigos de cardiologia
publicados entre {yesterday} e {today_str} (data de publicação ORIGINAL no site,
não data de indexação) nos seguintes sites:

- ahajournals.org (Circulation, Hypertension, Stroke)
- jacc.org (JACC family of journals)
- academic.oup.com/eurheartj (European Heart Journal)
- escardio.org/news (ESC press)
- medscape.com (cardiology section)
- scielo.br (Arquivos Brasileiros de Cardiologia)

Para CADA item encontrado, retorne em formato JSON ARRAY:
{{
  "url": "URL real verificada",
  "titulo": "TÍTULO LITERAL DA PÁGINA — copiar exato, não parafrasear",
  "fonte": "Nome do site (Circulation, JACC, EHJ, ESC News, Medscape, etc)",
  "data_publicacao": "YYYY-MM-DD do site",
  "doi": "se visível na página, senão null"
}}

REGRAS RÍGIDAS:
- NÃO sintetize abstract
- NÃO interprete o conteúdo
- NÃO invente número, autor, ou estatística
- NÃO inclua se não conseguir verificar a data ≤2 dias
- Apenas LISTAR. Outro modelo vai analisar depois.

Retorne APENAS o JSON array, sem markdown, sem explicação."""

    try:
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.1,
        )
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=fetcher_prompt,
            config=config,
        )
        text = response.text.strip()
        print(f"✓ Response received ({len(text)} chars)")
        print(f"\nFirst 2000 chars of output:")
        print(text[:2000])
        print()

        # Try to parse as JSON
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            articles = json.loads(cleaned)
            print(f"✓ Parsed as JSON: {len(articles)} articles")
            print()
            for i, a in enumerate(articles[:5], 1):
                print(f"  [{i}] {a.get('fonte', '?')}: {a.get('titulo', '?')[:80]}")
                print(f"      Date: {a.get('data_publicacao', '?')} | DOI: {a.get('doi', 'null')}")
                print(f"      URL: {a.get('url', '?')[:100]}")
                print()
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parse failed: {e}")
            print("  (Output may need prompt tuning)")

        # Show grounding metadata if available
        if hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if hasattr(cand, "grounding_metadata") and cand.grounding_metadata:
                gm = cand.grounding_metadata
                if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                    print(f"\n📚 Grounding sources cited: {len(gm.grounding_chunks)}")
                    for i, chunk in enumerate(gm.grounding_chunks[:5], 1):
                        if hasattr(chunk, "web") and chunk.web:
                            print(f"  [{i}] {chunk.web.title or '?'} — {chunk.web.uri or '?'}")
        print()
    except Exception as e:
        print(f"✗ TEST 2 FAILED: {type(e).__name__}: {e}")
        # Don't exit — continue to test 3
        print()

    # ============================================================
    # TEST 3: YouTube URL analysis (gemini-2.5-flash)
    # Use a known cardio video — ESC TV HFA Day 1
    # ============================================================
    print("─" * 70)
    print("TEST 3: YouTube URL analysis (gemini-2.5-flash)")
    print("─" * 70)

    # Use a known cardio YouTube video
    # ESC TV HFA Wrap-up Day 1 - HeartFailure26
    test_video_url = "https://www.youtube.com/watch?v=yX2hyNZRjc4"

    youtube_prompt = """Analise este vídeo de cardiologia e retorne em JSON:
{
  "tema": "tópico principal em PT-BR (5-10 palavras)",
  "resumo_curto": "2-3 frases em PT-BR sobre o que foi discutido",
  "bullets": [
    "Ponto-chave 1 em PT-BR (~80 chars)",
    "Ponto-chave 2 em PT-BR",
    "Ponto-chave 3 em PT-BR"
  ],
  "estudos_citados": ["Nome do estudo se mencionado, ou []"],
  "speakers": ["Nome do palestrante se identificável, ou []"]
}

REGRAS:
- NÃO invente números, percentuais ou nomes de autores
- Se não tem certeza, deixe vazio ou null
- PT-BR brasileiro coloquial mas técnico
- Retorne APENAS o JSON, sem markdown, sem explicação."""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Part(file_data=types.FileData(file_uri=test_video_url)),
                youtube_prompt,
            ],
        )
        text = response.text.strip()
        print(f"✓ Response received ({len(text)} chars)")
        print(f"\nVideo URL: {test_video_url}")
        print(f"\nFull output:")
        print(text)
        print()

        # Try parse
        cleaned = text
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            data = json.loads(cleaned)
            print(f"\n✓ Parsed as JSON")
            print(f"  Tema: {data.get('tema', '?')}")
            print(f"  Bullets: {len(data.get('bullets', []))}")
            print(f"  Estudos citados: {data.get('estudos_citados', [])}")
            print(f"  Speakers: {data.get('speakers', [])}")
        except json.JSONDecodeError as e:
            print(f"⚠ JSON parse failed: {e}")
        print()
    except Exception as e:
        print(f"✗ TEST 3 FAILED: {type(e).__name__}: {e}")
        print()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("=" * 70)
    print("TESTE EMPÍRICO COMPLETO")
    print("=" * 70)
    print()
    print("Avalie os outputs acima:")
    print("  TEST 1: API key + connectivity OK?")
    print("  TEST 2: Gemini consegue listar artigos cardio recentes via Google Search?")
    print("  TEST 3: Gemini consegue analisar vídeo YouTube?")
    print()
    print("Se todos os 3 passaram com qualidade aceitável → seguir para Fase 3")
    print("Se algum falhou → ajustar prompt ou estratégia antes de continuar")


if __name__ == "__main__":
    main()
