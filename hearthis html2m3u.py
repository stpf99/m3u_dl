import re

def find_mp3_links(html_content):
    # Dopasowuje linki zaczynające się od https://, zawierające .mp3?s=... i ucinające przed znakiem &
    pattern = re.compile(r'(https://[^\s"]+?\.mp3\?s=[^&\s"]+)')
    return pattern.findall(html_content)

def export_to_m3u(links, output_file='playlist.m3u'):
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        for link in links:
            f.write(link + '\n')

# Przykład użycia:
with open('mtmn_hearthis.at.html', 'r', encoding='utf-8') as file:
    html_content = file.read()

links = find_mp3_links(html_content)
export_to_m3u(links)

# Podgląd wyników w terminalu
for link in links:
    print(link)
