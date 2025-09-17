# import socket
# import XVM
# import threading
# # UDP_IP = "18.229.150.174"
# # UDP_IP = "18.228.195.73"
# # UDP_IP = "136.248.106.123"
# UDP_IP = "localhost"
# UDP_PORT = 9999

# sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


# def receiveMessage():
#     while True:
#         msg = sock.recv(4096)
#         print(f"msg recebida: {msg}")
        

# threading.Thread(target=receiveMessage).start()

# while True:
#     message = input("Digite a mensagem a ser enviada (ou 'exit' para sair): ")
#     if message == "exit":
#         break
#     else:
#         xvm = XVM.generateXVM('0306','8000',message)

#     sock.sendto(xvm.encode(), (UDP_IP, UDP_PORT))
#     print(f"Mensagem '{xvm}' enviada para {UDP_IP}:{UDP_PORT}")

# sock.close()




import socket
import XVM
import threading
import re

UDP_IP = "localhost"
UDP_PORT = 9999

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def send_sfb_message(message: bytes):
    """
    Envia uma mensagem SFB diretamente pelo socket UDP.
    """
    sock.sendto(message, (UDP_IP, UDP_PORT))

def send_xvm_message(message):
    """
    Gera a mensagem no formato XVM e envia pelo socket UDP como bytes.
    """
    xvm_msg = XVM.generateXVM('0308','8000',message)
    sock.sendto(xvm_msg.encode(), (UDP_IP, UDP_PORT))
    print(f"Mensagem enviada: {xvm_msg}")


def parse_xvm_message(msg_bytes):
    """
    Recebe uma mensagem (bytes ou string), faz split usando qualquer caractere não alfanumérico,
    pega a primeira parte, troca o primeiro 'S' por 'R' e retorna o resultado.
    """
    if isinstance(msg_bytes, bytes):
        msg_str = msg_bytes.decode()
    else:
        msg_str = str(msg_bytes)
    parts = re.split(r'[^a-zA-Z0-9]+', msg_str)
    if parts and parts[1]:
        if 'S' in parts[1]:
            result = parts[1].replace('S', 'R', 1)
            return result
    return ""

def generate_response(input_message: bytes) -> bytes:
    # Validate the input message starts with the expected header
    header = b"BINAVSFB"
    if not input_message.startswith(header):
        raise ValueError("Invalid input message header")

    # Extract the serial number (example: 9 bytes before the checksum)
    serial_number_offset = -13  # Adjust based on the protocol
    serial_number_length = 9
    serial_number = input_message[serial_number_offset:serial_number_offset + serial_number_length]

    # Extract the sequence (example: 4 bytes before the serial number)
    sequence_offset = serial_number_offset - 4
    sequence_length = 4
    sequence = input_message[sequence_offset:sequence_offset + sequence_length]

    # Construct the response
    response_header = b"BINAVRFB"
    ack_prefix = b"_ACK"
    padding = b"\x00" * 4  # Example padding
    checksum = b"\xC8\xB0"  # Example checksum (replace with actual calculation if needed)

    response = (
        response_header +
        serial_number +
        ack_prefix +
        sequence +
        padding +
        checksum
    )
    print(response.hex())
    return response





def receive_message():
    """
    Loop infinito para receber mensagens em bytes e enviar respostas automáticas.
    """
    while True:
        msg_bytes, addr = sock.recvfrom(4096)
        print(f"Mensagem recebida de {addr}: {msg_bytes}")
        
        if b">ACK" in msg_bytes:
            continue  
        if b"QSN" in msg_bytes:
            send_xvm_message('RSN123456789')
        # elif msg_bytes.startswith(b">S") or msg_bytes.startswith(b">V"):
            # send_xvm_message('RED')
        elif b"BINA" in msg_bytes:
            send_sfb_message(generate_response(msg_bytes))
        else:
            parsed_msg = parse_xvm_message(msg_bytes)
            if parsed_msg:
                send_xvm_message(parsed_msg)
            else:
                send_xvm_message('RED')


threading.Thread(target=receive_message, daemon=True).start()

while True:
    message = input("Digite a mensagem a ser enviada (ou 'exit' para sair): ")
    if message.lower() == "exit":
        break
    else:
        send_xvm_message(message)

sock.close()
