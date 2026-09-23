# Цахим шалгалтын Flask систем

## Фолдер
Шалгалт/
  app.py
  requirements.txt
  supabase.sql
  ААД/questions.txt
  Нарядын систем/questions.txt
  templates/
  static/

## questions.txt формат

205. Асуултын текст
A) Нэгдүгээр сонголт
B) Хоёрдугаар сонголт
C) Гуравдугаар сонголт
Зөв хариулт: B

206. Дараагийн асуулт
A) ...
B) ...
C) ...
D) ...
Зөв хариулт: D

Асуулт бүр хоосон мөрөөр тусгаарлагдана.

## Local
pip install -r requirements.txt
python app.py

## Render
Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

## Render Environment Variables
SUPABASE_URL=...
SUPABASE_SECRET_KEY=...
ADMIN_PASSWORD=...
SECRET_KEY=...

## Admin
https://YOUR-SITE.onrender.com/admin
