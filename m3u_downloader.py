import os
import re
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
import time

class M3UDownloader:
    def __init__(self, max_workers=4, chunk_size=8192, timeout=120):
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.lock = threading.Lock()
        self.downloaded = 0
        self.total = 0
        
    def parse_m3u(self, m3u_content):
        """Parsuje zawartość pliku M3U i zwraca listę (nazwa, url)"""
        lines = m3u_content.strip().split('\n')
        entries = []
        current_title = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # Wyciąga tytuł z linii EXTINF
                title_match = re.search(r'#EXTINF:[^,]*,(.+)', line)
                if title_match:
                    current_title = title_match.group(1).strip()
            elif line and not line.startswith('#') and current_title:
                # To jest URL
                entries.append((current_title, line))
                current_title = None
                
        return entries
    
    def sanitize_filename(self, filename):
        """Czyści nazwę pliku z niedozwolonych znaków"""
        # Usuwa/zamienia znaki niedozwolone w nazwach plików
        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        filename = re.sub(r'\s+', '_', filename)  # Spacje na podkreślenia
        # Skraca jeśli za długa
        if len(filename) > 200:
            filename = filename[:200]
        return filename
    
    def download_file(self, title, url, output_dir="downloads"):
        """Pobiera pojedynczy plik"""
        try:
            # Przygotuj nazwę pliku
            safe_title = self.sanitize_filename(title)
            filename = f"{safe_title}.mp3"
            filepath = os.path.join(output_dir, filename)
            
            # Sprawdź czy plik już istnieje
            if os.path.exists(filepath):
                print(f"⚠️  Plik już istnieje: {filename}")
                with self.lock:
                    self.downloaded += 1
                return True
            
            print(f"📥 Pobieranie: {filename}")
            
            # Pobierz plik
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            # Zapisz plik
            os.makedirs(output_dir, exist_ok=True)
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    if chunk:
                        f.write(chunk)
            
            file_size = os.path.getsize(filepath)
            print(f"✅ Pobrano: {filename} ({file_size/1024/1024:.1f} MB)")
            
            with self.lock:
                self.downloaded += 1
                
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Błąd pobierania {title}: {e}")
            return False
        except Exception as e:
            print(f"❌ Nieoczekiwany błąd dla {title}: {e}")
            return False
    
    def download_m3u(self, m3u_file_path, output_dir="downloads"):
        """Pobiera wszystkie pliki z M3U"""
        try:
            # Wczytaj plik M3U
            with open(m3u_file_path, 'r', encoding='utf-8') as f:
                m3u_content = f.read()
        except UnicodeDecodeError:
            # Spróbuj z innym kodowaniem
            with open(m3u_file_path, 'r', encoding='latin-1') as f:
                m3u_content = f.read()
        
        # Parsuj M3U
        entries = self.parse_m3u(m3u_content)
        
        if not entries:
            print("❌ Nie znaleziono żadnych wpisów w pliku M3U")
            return
        
        self.total = len(entries)
        self.downloaded = 0
        
        print(f"🎵 Znaleziono {self.total} plików do pobrania")
        print(f"📁 Katalog docelowy: {output_dir}")
        print(f"🧵 Używa {self.max_workers} wątków")
        print("-" * 50)
        
        start_time = time.time()
        
        # Pobieranie wielowątkowe
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Uruchom wszystkie zadania
            future_to_entry = {
                executor.submit(self.download_file, title, url, output_dir): (title, url)
                for title, url in entries
            }
            
            # Czekaj na zakończenie
            for future in as_completed(future_to_entry):
                title, url = future_to_entry[future]
                try:
                    success = future.result()
                    progress = (self.downloaded / self.total) * 100
                    print(f"📊 Postęp: {self.downloaded}/{self.total} ({progress:.1f}%)")
                except Exception as e:
                    print(f"❌ Error processing {title}: {e}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        print("-" * 50)
        print(f"🎉 Zakończono pobieranie!")
        print(f"✅ Pobrano: {self.downloaded}/{self.total} plików")
        print(f"⏱️  Czas: {duration:.1f} sekund")
        if self.downloaded > 0:
            print(f"⚡ Średnio: {duration/self.downloaded:.1f}s na plik")

def main():
    # Przykład użycia
    print("🎵 M3U Downloader - Wielowątkowy pobieracz")
    print("=" * 50)
    
    # Ścieżka do pliku M3U
    m3u_file = input("Podaj ścieżkę do pliku M3U: ").strip()
    
    if not os.path.exists(m3u_file):
        print(f"❌ Plik {m3u_file} nie istnieje!")
        return
    
    # Katalog docelowy
    output_dir = input("Katalog docelowy (domyślnie 'downloads'): ").strip()
    if not output_dir:
        output_dir = "downloads"
    
    # Liczba wątków
    try:
        workers = input("Liczba wątków (domyślnie 4): ").strip()
        workers = int(workers) if workers else 4
        workers = max(1, min(workers, 16))  # Ograniczenie 1-16
    except ValueError:
        workers = 4
    
    print(f"\n🚀 Rozpoczynam pobieranie z {workers} wątkami...")
    
    # Utwórz downloader i rozpocznij pobieranie
    downloader = M3UDownloader(max_workers=workers)
    downloader.download_m3u(m3u_file, output_dir)

if __name__ == "__main__":
    main()
