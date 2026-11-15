import os, sqlite3, hashlib, hmac, secrets, uuid
from pathlib import Path

DB=Path(__file__).with_name('energia_em_foco.db')

def cloud():
    try:
        import streamlit as st
        from supabase import create_client
        url=st.secrets.get('SUPABASE_URL',os.getenv('SUPABASE_URL',''))
        key=st.secrets.get('SUPABASE_SERVICE_ROLE_KEY',os.getenv('SUPABASE_SERVICE_ROLE_KEY',''))
        return create_client(url,key) if url and key else None
    except Exception: return None

def conn():
    c=sqlite3.connect(DB,timeout=10)
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('CREATE TABLE IF NOT EXISTS contas (id TEXT PRIMARY KEY, usuario TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS consumos (user_id TEXT NOT NULL, mes TEXT NOT NULL, consumo_kwh REAL NOT NULL CHECK(consumo_kwh>=0), tarifa REAL NOT NULL CHECK(tarifa>=0), PRIMARY KEY(user_id,mes), FOREIGN KEY(user_id) REFERENCES contas(id) ON DELETE CASCADE)')
    c.commit(); return c

def hash_password(password):
    salt=secrets.token_bytes(16)
    derived=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,260000)
    return salt.hex()+':'+derived.hex()

def verify(password, stored):
    try:
        salt,expected=stored.split(':')
        result=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),260000)
        return hmac.compare_digest(result,bytes.fromhex(expected))
    except Exception: return False

def register(username,password):
    username=username.strip().lower()
    if not 3<=len(username)<=30 or not all(c.isascii() and (c.isalnum() or c in '_-.') for c in username):
        raise ValueError('Use de 3 a 30 caracteres: letras sem acento, números, ponto, hífen ou _.')
    if len(password)<8 or len(password)>128: raise ValueError('A senha precisa ter entre 8 e 128 caracteres.')
    uid=str(uuid.uuid4()); hashed=hash_password(password)
    c=cloud()
    if c:
        if c.table('contas').select('id').eq('usuario',username).execute().data: raise ValueError('Esse usuário já existe.')
        try: c.table('contas').insert({'id':uid,'usuario':username,'senha_hash':hashed}).execute()
        except Exception: raise ValueError('Não foi possível cadastrar. Verifique se o usuário já existe.')
    else:
        with conn() as db:
            try: db.execute('INSERT INTO contas VALUES (?,?,?)',(uid,username,hashed))
            except sqlite3.IntegrityError: raise ValueError('Esse usuário já existe.')
    return uid

def authenticate(username,password):
    username=username.strip().lower(); c=cloud()
    if c:
        rows=c.table('contas').select('id,senha_hash').eq('usuario',username).limit(1).execute().data
        row=(rows[0]['id'],rows[0]['senha_hash']) if rows else None
    else:
        with conn() as db: row=db.execute('SELECT id,senha_hash FROM contas WHERE usuario=?',(username,)).fetchone()
    return row[0] if row and verify(password,row[1]) else None

def get_records(uid):
    c=cloud()
    if c: return c.table('consumos').select('mes,consumo_kwh,tarifa').eq('user_id',uid).order('mes').execute().data
    with conn() as db:
        return [{'mes':r[0],'consumo_kwh':r[1],'tarifa':r[2]} for r in db.execute('SELECT mes,consumo_kwh,tarifa FROM consumos WHERE user_id=? ORDER BY mes',(uid,))]

def save(uid,mes,kwh,tariff):
    c=cloud()
    if c: c.table('consumos').upsert({'user_id':uid,'mes':mes,'consumo_kwh':kwh,'tarifa':tariff},on_conflict='user_id,mes').execute()
    else:
        with conn() as db: db.execute('INSERT INTO consumos VALUES (?,?,?,?) ON CONFLICT(user_id,mes) DO UPDATE SET consumo_kwh=excluded.consumo_kwh,tarifa=excluded.tarifa',(uid,mes,kwh,tariff))

def delete(uid,mes):
    c=cloud()
    if c: c.table('consumos').delete().eq('user_id',uid).eq('mes',mes).execute()
    else:
        with conn() as db: db.execute('DELETE FROM consumos WHERE user_id=? AND mes=?',(uid,mes))

def delete_account(uid):
    c=cloud()
    if c: c.table('contas').delete().eq('id',uid).execute()
    else:
        with conn() as db: db.execute('DELETE FROM contas WHERE id=?',(uid,))
