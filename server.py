#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hukukİçtihat+ Ceza V4.2
a-Shell mini uyumlu HTTP sunucusu

Bu sunucu standart `python3 -m http.server` yerine kullanılmalıdır.
a-Shell mini'nin iOS sandbox ortamında oluşan şu hataları tolere eder:
- NoneType client_address hatası
- BrokenPipeError
- ConnectionResetError

Kullanım:
    python3 server.py
    
Tarayıcıda:
    http://127.0.0.1:8000
"""

import http.server
import socketserver
import os
import sys

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__)) or "."


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """
    a-Shell mini uyumlu HTTP istek işleyici.
    
    Özellikler:
    - NoneType client_address toleransı
    - Sessiz hata yönetimi
    - Türkçe karakter desteği için UTF-8 encoding
    """
    
    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = DIRECTORY
        super().__init__(*args, directory=directory, **kwargs)
    
    def log_message(self, format, *args):
        """
        İstek loglarını yazdırır.
        client_address None olabilir (a-Shell mini sorunu).
        """
        try:
            if self.client_address and len(self.client_address) >= 1:
                addr = self.client_address[0]
            else:
                addr = "unknown"
            sys.stderr.write("[%s] %s\n" % (addr, format % args))
        except Exception:
            pass
    
    def log_error(self, format, *args):
        """
        Hata loglarını yazdırır.
        a-Shell mini'de bazı hatalar sessizce geçilir.
        """
        try:
            self.log_message(format, *args)
        except Exception:
            pass
    
    def handle_one_request(self):
        """
        Tek bir HTTP isteğini işler.
        BrokenPipeError ve ConnectionResetError toleranslı.
        """
        try:
            super().handle_one_request()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception as e:
            try:
                self.log_error("İstek işleme hatası: %s", str(e))
            except Exception:
                pass
    
    def send_response(self, code, message=None):
        """
        HTTP yanıtı gönderir.
        Bağlantı kopması durumunda sessizce devam eder.
        """
        try:
            super().send_response(code, message)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
    
    def end_headers(self):
        """
        HTTP başlıklarını sonlandırır.
        CORS desteği ekler (yerel geliştirme için).
        """
        try:
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-cache')
            super().end_headers()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
    
    def copyfile(self, source, outputfile):
        """
        Dosya içeriğini yanıta kopyalar.
        Bağlantı kopması durumunda sessizce devam eder.
        """
        try:
            super().copyfile(source, outputfile)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass


class SafeTCPServer(socketserver.TCPServer):
    """
    a-Shell mini uyumlu TCP sunucusu.
    
    Özellikler:
    - SO_REUSEADDR aktif (port hızlı serbest bırakma)
    - NoneType client_address toleransı
    - Sessiz hata yönetimi
    """
    
    allow_reuse_address = True
    
    def get_request(self):
        """
        Yeni bağlantı kabul eder.
        client_address None olabilir (a-Shell mini sorunu).
        """
        try:
            conn, addr = self.socket.accept()
            if addr is None:
                addr = ("127.0.0.1", 0)
            return conn, addr
        except Exception as e:
            raise
    
    def handle_error(self, request, client_address):
        """
        Bağlantı hatalarını sessizce yönetir.
        a-Shell mini'de sık oluşan hatalar loglanmaz.
        """
        try:
            exc_type = sys.exc_info()[0]
            if exc_type in (BrokenPipeError, ConnectionResetError, 
                           ConnectionAbortedError, OSError):
                return
            super().handle_error(request, client_address)
        except Exception:
            pass
    
    def server_close(self):
        """
        Sunucuyu güvenli şekilde kapatır.
        """
        try:
            super().server_close()
        except Exception:
            pass


def main():
    """
    Sunucuyu başlatır.
    """
    os.chdir(DIRECTORY)
    
    print("=" * 50)
    print("Hukukİçtihat+ Ceza V4.2")
    print("a-Shell mini uyumlu HTTP Sunucusu")
    print("=" * 50)
    print()
    print(f"Dizin: {DIRECTORY}")
    print(f"Port: {PORT}")
    print()
    print("Tarayıcıda aç:")
    print(f"  http://127.0.0.1:{PORT}")
    print(f"  http://localhost:{PORT}")
    print()
    print("Durdurmak için: Ctrl+C")
    print("=" * 50)
    print()
    
    try:
        with SafeTCPServer(("", PORT), QuietHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nSunucu durduruldu.")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"\nHata: Port {PORT} zaten kullanımda.")
            print("Çözüm: Önce mevcut sunucuyu durdurun veya farklı port kullanın.")
        else:
            print(f"\nHata: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nBeklenmeyen hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
