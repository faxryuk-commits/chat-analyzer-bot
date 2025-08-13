#!/usr/bin/env python3
"""
HTTPS сервер для локальной разработки WebApp
"""

import ssl
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class HTTPSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def run_https_server():
    """Запускает HTTPS сервер на порту 8443"""
    server_address = ('localhost', 8443)
    
    # Создаем SSL контекст
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    
    # Генерируем самоподписанный сертификат
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    import datetime
    
    # Генерируем приватный ключ
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    # Создаем сертификат
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "RU"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Moscow"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, "Moscow"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Chat Analyzer Bot"),
        x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
    ])
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        private_key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=365)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName("localhost"),
            x509.IPAddress("127.0.0.1"),
        ]),
        critical=False,
    ).sign(private_key, hashes.SHA256())
    
    # Сохраняем сертификат и ключ
    with open("cert.pem", "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))
    
    with open("key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))
    
    # Настраиваем SSL контекст
    context.load_cert_chain("cert.pem", "key.pem")
    
    # Создаем HTTPS сервер
    httpd = HTTPServer(server_address, HTTPSRequestHandler)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
    
    print(f"🌐 HTTPS сервер запущен на https://localhost:8443")
    print(f"📁 Обслуживает файлы из текущей директории")
    print(f"🔒 Использует самоподписанный сертификат")
    print(f"⚠️  В браузере может появиться предупреждение о безопасности")
    print(f"💡 Нажмите 'Дополнительно' -> 'Перейти на localhost (небезопасно)'")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 HTTPS сервер остановлен")
        # Удаляем временные файлы
        if os.path.exists("cert.pem"):
            os.remove("cert.pem")
        if os.path.exists("key.pem"):
            os.remove("key.pem")

if __name__ == '__main__':
    run_https_server()
