import requests
import urllib.request
from bs4 import BeautifulSoup

# Estabelecendo conexÃ£o com o servidor da pÃ¡gina e puxando o conteÃºdo.
response = requests.get('https://www.nytimes.com/international/')
content = response.content
site_html = BeautifulSoup(content, 'html.parser')

# Encontrando o elemento desejado.
img = site_html.findAll('img', attrs={'alt':'Visitors to the ONX Studio in Manhattan with Ashley Zelinskieâs âRing Nebulaâ (2022), a 3-D printed sculpture, during the exhibition âUnfolding the Universe.â'})
link = img[1].attrs['src']

# Realizando o download a partir do img src.
urllib.request.urlretrieve(f'{link}', 'img.png')
