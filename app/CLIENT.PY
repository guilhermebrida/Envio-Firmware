import socket
import XVM

# UDP_IP = "192.168.0.116"
# UDP_IP = "191.4.146.247"
# UDP_IP = "191.4.157.126"
UDP_IP = "18.230.78.246"
UDP_PORT = 10116

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    message = input("Digite a mensagem a ser enviada (ou 'exit' para sair): ")
    if message == "exit":
        break
    else:
        xvm = XVM.generateXVM('0306','8000',message)

    sock.sendto(xvm.encode(), (UDP_IP, UDP_PORT))
    print(f"Mensagem '{xvm}' enviada para {UDP_IP}:{UDP_PORT}")

sock.close()