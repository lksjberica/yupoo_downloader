import argparse
import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
from tqdm import tqdm
from PIL import Image
import piexif
from datetime import datetime

def sanitize_filename(name: str) -> str:
    """Sanitizes a string to be a valid filename."""
    name = re.sub(r"[\\/:*?\"<>|]", "_", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name or "yupoo_image"

def clean_image_metadata(file_path: str):
    """Removes EXIF metadata from an image using Piexif."""
    try:
        piexif.remove(file_path)
        print(f"Metadados removidos de: {os.path.basename(file_path)}")
    except Exception as e:
        print(f"Erro ao limpar metadados de {os.path.basename(file_path)}: {e}")

def download_images(album_url, output_dir):
    """
    Downloads images from a Yupoo album and processes them.
    """
    print(f"\n--- Processando álbum: {album_url} ---")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36',
        'Referer': album_url,
    }
    
    try:
        response = requests.get(album_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a URL: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    page_title = soup.find('title').text
    sanitized_title = sanitize_filename(page_title).replace(" - Yupoo", "").strip()
    
    print(f"Título do álbum encontrado: '{sanitized_title}'")
    
    album_output_dir = os.path.join(output_dir, sanitized_title)
    if not os.path.exists(album_output_dir):
        os.makedirs(album_output_dir)
    
    # --- NOVO: Cria o arquivo de metadados ---
    metadata_path = os.path.join(album_output_dir, "_metadados.txt")
    with open(metadata_path, 'w', encoding='utf-8') as f:
        f.write(f"URL do álbum: {album_url}\n")
        f.write(f"Data e hora do download: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
    print("Arquivo de metadados criado.")
    # ----------------------------------------

    best_urls = {}
    
    for img in soup.find_all('img'):
        candidates = []
        
        for attr in ['data-original', 'data-src', 'src']:
            url = img.get(attr)
            if url:
                candidates.append(url)
        
        srcset = img.get('srcset')
        if srcset:
            for part in srcset.split(','):
                url_part = part.strip().split()[0]
                candidates.append(url_part)
        
        for url in candidates:
            if url and ('photo.yupoo.com' in url or 'yupoo.com/photo' in url):
                full_url = urljoin(album_url, url)
                
                match = re.search(r'yupoo\.com/(.*?)/[a-f0-9]+', full_url)
                if match:
                    base_key = match.group(0)
                    
                    if base_key not in best_urls:
                        best_urls[base_key] = full_url
                    else:
                        current_best = best_urls[base_key].lower()
                        new_candidate = full_url.lower()

                        if 'original' in new_candidate:
                            best_urls[base_key] = full_url
                        elif 'raw' in new_candidate and 'original' not in current_best:
                            best_urls[base_key] = full_url
                        elif 'big' in new_candidate and 'original' not in current_best and 'raw' not in current_best:
                            best_urls[base_key] = full_url
    
    image_links = list(best_urls.values())
    print(f"Encontradas {len(image_links)} imagens para download.")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i, url in enumerate(image_links):
        try:
            print(f"Baixando imagem {i+1}/{len(image_links)}: {url}")
            
            headers['Referer'] = album_url
            img_response = requests.get(url, headers=headers, timeout=30, stream=True)
            img_response.raise_for_status()

            file_name = f"{i+1:02d}.jpg"
            file_path = os.path.join(album_output_dir, file_name)
            
            with open(file_path, 'wb') as f:
                total_size = int(img_response.headers.get('content-length', 0))
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=file_name, leave=False) as pbar:
                    for chunk in img_response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
            
            if os.path.getsize(file_path) > 0:
                print("Download concluído com sucesso.")
                clean_image_metadata(file_path)
            else:
                print("ERRO: O arquivo foi baixado, mas está vazio. Excluindo...")
                os.remove(file_path)

        except requests.exceptions.RequestException as e:
            print(f"Falha ao baixar {url}: {e}")

    print(f"\nPronto. Imagens salvas em: {album_output_dir}")

def main():
    print("--- Yupoo Album Downloader ---")
    print("Digite as URLs dos álbuns. Pressione Enter em uma linha vazia para começar o download.")
    
    urls = []
    for i in range(10):  # Limite de 10 links por vez
        url = input(f"URL do álbum {i+1} (ou Enter para continuar): ").strip()
        if not url:
            break
        urls.append(url)
    
    if not urls:
        print("Nenhuma URL fornecida. Encerrando o programa.")
        return

    output_dir = "C:\\Yupoo\\downloads"
    
    for url in urls:
        download_images(url, output_dir)
        
    print("\n--- Todos os downloads foram concluídos! ---")

if __name__ == "__main__":
    main()