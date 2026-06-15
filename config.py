# -*- coding: utf-8 -*-
"""CONFIGURACIÓN - API Keys y constantes"""
import os, streamlit as st
from dotenv import load_dotenv

load_dotenv() # Cargar variables de entorno al inicio

def get_gemini_api_key():
    try:
        if hasattr(st, 'secrets') and 'GEMINI_API_KEY' in st.secrets: return st.secrets['GEMINI_API_KEY']
    except: pass
    try:
        with open('.env', 'r') as f:
            for linea in f:
                if 'GEMINI_API_KEY' in linea: return linea.split('=', 1)[1].strip().strip('"').strip("'")
    except: pass
    return os.environ.get('GEMINI_API_KEY', '')

def get_groq_api_key():
    try:
        if hasattr(st, 'secrets') and 'GROQ_API_KEY' in st.secrets: return st.secrets['GROQ_API_KEY']
    except: pass
    try:
        with open('.env', 'r') as f:
            for linea in f:
                if 'GROQ_API_KEY' in linea: return linea.split('=', 1)[1].strip().strip('"').strip("'")
    except: pass
    return os.environ.get('GROQ_API_KEY', '')

def get_deepseek_api_key():
    try:
        if hasattr(st, 'secrets') and 'DEEPSEEK_API_KEY' in st.secrets: return st.secrets['DEEPSEEK_API_KEY']
    except: pass
    try:
        with open('.env', 'r') as f:
            for linea in f:
                if 'DEEPSEEK_API_KEY=' in linea: return linea.split('=', 1)[1].strip().strip('"').strip("'")
    except: pass
    return os.environ.get('DEEPSEEK_API_KEY', '')
