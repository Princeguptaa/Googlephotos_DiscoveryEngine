from bs4 import BeautifulSoup
with open('scratch/forum_html2.txt', 'r', encoding='utf-8') as f:
    soup = BeautifulSoup(f, 'html.parser')
node = soup.select_one('[class*="Questioncardcontent"]')
if node:
    print(node.get_text(strip=True)[:500])
else:
    print("Node not found")
