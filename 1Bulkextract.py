#!/usr/bin/env python3
"""
Enhanced ARGO Data Downloader + JSON Converter + RAG Embeddings + Mistral Summaries
Organized folder structure:
 - Dataset/YEAR/MONTH/*.nc
 - Datasetjson/YEAR/MONTH/*.json   (AI summaries)
 - VectorIndex/YEAR/MONTH/*.index  (FAISS embeddings)
"""

import os
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin
from datetime import datetime

import requests
from bs4 import BeautifulSoup
import xarray as xr
import json

from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

from langchain_groq import ChatGroq
from langchain.prompts import PromptTemplate
from pydantic import SecretStr


# -------------------------------
# Enhanced Downloader Class
# -------------------------------
class EnhancedArgoDownloader:
    def __init__(self, base_folder="Dataset", json_folder="Datasetjson", index_folder="VectorIndex"):
        self.base_folder = Path(base_folder)
        self.json_folder = Path(json_folder)
        self.index_folder = Path(index_folder)

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Embedding model
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        self.llm = ChatGroq(
            api_key=SecretStr(os.getenv("GROQ_API_KEY", "")),
            model="mistral-7b-instruct",
            # model="mistral-7b-instruct",
            temperature=0.2,
            max_tokens=256
        )

        # Ensure folders exist
        self.base_folder.mkdir(parents=True, exist_ok=True)
        self.json_folder.mkdir(parents=True, exist_ok=True)
        self.index_folder.mkdir(parents=True, exist_ok=True)

        print("🌊 Enhanced ARGO Downloader + RAG + Mistral Summaries initialized")
        print(f"📂 NC Base: {self.base_folder}")
        print(f"📂 JSON Base: {self.json_folder}")
        print(f"📂 Index Base: {self.index_folder}")
        print("=" * 60)

    # -------------------------------
    # File Listing & Download
    # -------------------------------
    def list_netcdf_files(self, url):
        try:
            resp = self.session.get(url, timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            return [urljoin(url, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.nc')]
        except Exception as e:
            print(f"❌ Error listing {url}: {e}")
            return []

    def download_file(self, url, folder):
        filename = url.split("/")[-1]
        local_path = folder / filename
        if local_path.exists():
            return local_path
        try:
            r = self.session.get(url, stream=True, timeout=60)
            r.raise_for_status()
            with open(local_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)
            print(f"✅ Downloaded {filename}")
            return local_path
        except Exception as e:
            print(f"❌ Failed {filename}: {e}")
            return None

    # -------------------------------
    # JSON + Embeddings
    # -------------------------------
    def enhance_summary(self, variable, sample):
        """Use Mistral to generate 2-line enriched summary"""
        prompt = PromptTemplate(
            input_variables=["var", "sample"],
            template=(
                "You are an oceanography assistant. "
                "Summarize the variable '{var}' with the sample value '{sample}' "
                "in 2 lines. Focus on keywords useful for Indian research, climate, "
                "and monsoon studies. Be concise and relevant."
            )
        )
        try:
            response = (prompt | self.llm).invoke({"var": variable, "sample": str(sample)})
            return response.content.strip()
        except Exception as e:
            print(f"⚠️ Summary generation failed for {variable}: {e}")
            return f"Variable {variable}, sample {sample}"

    def convert_nc_to_json(self, nc_path, json_path):
        try:
            ds = xr.open_dataset(nc_path)
            summaries = []
            for var in ds.data_vars:
                data = ds[var]
                sample = (
                    data.isel({dim: 0 for dim in data.dims}).values.item()
                    if data.values.size > 0 else "N/A"
                )
                summary = self.enhance_summary(var, sample)
                summaries.append({
                    "file": nc_path.name,
                    "variable": var,
                    "summary": summary
                })
            out = {"file": nc_path.name, "summaries": summaries}
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w") as f:
                json.dump(out, f, indent=2)
            print(f"📄 JSON saved → {json_path}")
            return out
        except Exception as e:
            print(f"❌ Failed to convert {nc_path}: {e}")
            return None

    def build_embeddings(self, json_data, index_path):
        try:
            texts = [s["summary"] for s in json_data["summaries"]]
            if not texts:
                return
            embeddings = self.model.encode(texts)
            d = embeddings.shape[1]
            index = faiss.IndexFlatL2(d)
            index.add(np.array(embeddings).astype("float32"))
            index_path.parent.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(index_path))
            print(f"📦 FAISS index saved → {index_path}")
        except Exception as e:
            print(f"❌ Embedding error: {e}")

    # -------------------------------
    # Process
    # -------------------------------
    def process_month(self, year, month, max_workers=3):
        base_url = f"https://data-argo.ifremer.fr/geo/indian_ocean/{year}/{month:02d}/"
        nc_folder = self.base_folder / str(year) / f"{month:02d}"
        json_folder = self.json_folder / str(year) / f"{month:02d}"
        index_folder = self.index_folder / str(year) / f"{month:02d}"
        nc_folder.mkdir(parents=True, exist_ok=True)

        files = self.list_netcdf_files(base_url)
        if not files:
            print(f"❌ No files found for {year}/{month:02d}")
            return

        print(f"📅 {year}/{month:02d}: {len(files)} files found")

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(self.download_file, url, nc_folder) for url in files]
            for fut in as_completed(futures):
                nc_path = fut.result()
                if nc_path:
                    json_path = json_folder / (nc_path.stem + ".json")
                    data = self.convert_nc_to_json(nc_path, json_path)
                    if data:
                        index_path = index_folder / (nc_path.stem + ".index")
                        self.build_embeddings(data, index_path)

    def process_year(self, year, max_workers=3):
        for month in range(1, 13):
            self.process_month(year, month, max_workers)


# -------------------------------
# Query RAG
# -------------------------------
def query_rag(query, index_path, top_k=3, model_name="sentence-transformers/all-MiniLM-L6-v2"):
    """Retrieve FAISS matches and use Mistral to answer"""
    model = SentenceTransformer(model_name)
    index = faiss.read_index(str(index_path))
    q_emb = model.encode([query]).astype("float32")
    D, I = index.search(q_emb, top_k)

    # Load JSON summaries
    json_path = Path(str(index_path).replace(".index", ".json"))
    if json_path.exists():
        with open(json_path) as f:
            data = json.load(f)
        matches = [data["summaries"][i]["summary"] for i in I[0] if i < len(data["summaries"])]
    else:
        matches = []

    # Use Mistral to generate final answer
    llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"), model="mistral-7b-instruct")
    context = "\n".join(matches)
    prompt = f"Answer the query based on the following summaries:\n{context}\n\nQuery: {query}\nAnswer:"
    try:
        resp = llm.invoke(prompt)
        return resp.content.strip(), matches
    except Exception as e:
        return f"⚠️ Error answering query: {e}", matches


# -------------------------------
# Main
# -------------------------------
def main():
    print("🌊 ENHANCED ARGO DOWNLOADER + RAG + MISTRAL SUMMARIES")
    downloader = EnhancedArgoDownloader()

    try:
        year_input = input("Enter year (e.g., 2024) [default=current year]: ").strip()
        year = int(year_input) if year_input else datetime.now().year
    except ValueError:
        print("⚠️ Invalid input, defaulting to current year.")
        year = datetime.now().year

    downloader.process_year(year)


if __name__ == "__main__":
    main()
