import socket
import XVM
import re
# import psycopg2
import os
import time
import asyncio
import selectors
import time
from tenacity import retry, stop_after_delay, wait_fixed, stop_after_attempt, TryAgain
from sqlalchemy import create_engine, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

ips = []
ALREADY_LISTEN = []
RSN_DICT = {}
VOZ = []
cabeçalho =  'BINAVSFB'
bloc =''
bloco =[]
path = []
ID=[]
blocos_envio = []
arquivos = None
BLOCOS = []
LISTENED = []

postgres_host = os.environ['POSTGRES_HOST']
postgres_port = os.environ['POSTGRES_PORT']
postgres_user = os.environ['POSTGRES_USER']
postgres_password = os.environ['POSTGRES_PASSWORD']
postgres_db = os.environ['POSTGRES_DB']

connection = psycopg2.connect(
    host=postgres_host,
    # host="postgres",
    port=postgres_port,
    user=postgres_user,
    password=postgres_password,
    dbname=postgres_db
)

cursor = connection.cursor()

# engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
engine = create_engine(f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}')


host = '0.0.0.0'
porta = 10116
equipamentos_executados = {}
blocos_de_dados = [...]  



Base = declarative_base()

class Firmware(Base):
    __tablename__ = 'firmware'

    device_id = Column(String, primary_key=True)
    SN = Column(String, nullable=False)
    content_blocs = Column(LargeBinary)
    blocs_acks = Column(LargeBinary)
    send_datetime = Column(DateTime, default=func.timezone('America/Sao_Paulo', func.now()))
    reception_datetime = Column(DateTime, default=func.timezone('America/Sao_Paulo', func.now()))


Session = sessionmaker(bind=engine)
session = Session()



novo_firmware = Firmware(
    device_id='id_do_dispositivo',
    SN='numero_de_serie',
    content_blocs=b'conteudo_blocos', 
    blocs_acks=b'acks_dos_blocos',    
    send_datetime=datetime.now(),
    reception_datetime=datetime.now()
)

session.add(novo_firmware)
session.commit()


def Arquivos(device_id):
        print(device_id)
        sn = RSN_DICT[device_id]
        print(path_voz)
        for files in path_voz:
            f=open(f'{files}','rb')
            conteudo = f.read()
            separar = [conteudo[i:i+520]for i in range(0,len(conteudo),520)]
            print('\n',files,'\n')
            msg = '80000000'
            for i in range(len(separar)):
                bloco = cabeçalho.encode().hex()+separar[i].hex()+sn.encode().hex()
                sep = re.findall('........',bloco)
                sep.append(msg)
                cs =  crc(sep)
                bloc = bloco+msg+cs
                msg = int(msg,16)+1
                msg = format(msg,'X')
                b = bytes.fromhex(bloc)
                BLOCOS.append(b)
        return BLOCOS



def crc(x): 
    cs_int = 0
    sep = x
    for i in range(len(sep)):
        cs_int ^= (int(sep[i],16)) 
    hexcs = hex(cs_int).replace('0x','')
    return hexcs   

def find(pasta):
    arquivos = os.listdir(pasta)
    print(arquivos)
    for arquivo in arquivos:
        # print('puro',arquivo)
        caminho_arquivo = os.path.join(pasta, arquivo)
        if os.path.isfile(caminho_arquivo):
            path.append(caminho_arquivo)
    return path


# async def enviar_bloco(sock, bloco, endereco):
    # sock.sendto(bloco, endereco)
    # await asyncio.wait_for(receber_resposta(sock), timeout=3)
    # await receber_resposta(sock)
    

def solicitar_serial_number(sock, device_id, addr):
    xvm = XVM.generateXVM(device_id, str(8000).zfill(4), '>QSN<')
    print(xvm)
    response = enviar_mensagem_udp(sock,addr,xvm)
    result = re.search('>RSN.*', response.decode())
    if result is not None:
        rsn = result.group()
        sn = rsn.split('_')[0].split('>RSN')[1]
        if sn:
            LISTENED.append(device_id)
            RSN_DICT[device_id] = sn

@retry(stop=stop_after_attempt(30), wait=wait_fixed(2))
def enviar_mensagem_udp(sock, addr, mensagem):
    timeout = 3
    if type(mensagem) == bytes:
        sock.sendto(mensagem, addr)
    else:
        print(mensagem)
        sock.sendto(mensagem.encode(), addr)
    start_time = time.time()
    response, _ = sock.recvfrom(1024)
    print(response)
    if re.search(b'RUV.*',response) or re.search(b'.*NAK.*',response):
        raise TryAgain
    if time.time() - start_time >= timeout:
        print("timeout")
        raise TryAgain
    return response


# async def receber_resposta(sock):
#     timeout = 5
#     start_time = time.time()
#     response, _ = sock.recvfrom(1024)
#     if time.time() - start_time >= timeout:
#         return False
#     print('Resposta:', response)



def criar(device_id,vozes):
    try:
        sn = RSN_DICT[device_id]
        cursor.execute('INSERT INTO vozes ("IMEI", "SN", "VOZES") values (\'{}\', \'{}\', \'{}\');'.format(device_id, sn,vozes))
        connection.commit()
    except:
        pass
    finally:
        cursor.execute('SELECT "IMEI" FROM vozes;')
        results = cursor.fetchall()
        ID = [result[0] for result in results]
        print('Ids no banco:',ID)


async def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, porta))
    # sock.setblocking(False)
    while True:
        data, addr = sock.recvfrom(1024)
        ip_equipamento = addr[0]
        # if ip_equipamento not in equipamentos_executados:
        if re.search('BINA.*',data.decode(errors='ignore')) is None:
            xvmMessage = XVM.parseXVM(data.decode(errors='ignore'))
            msg = xvmMessage[0]
            device_id = xvmMessage[1]
        if device_id not in RSN_DICT:
            solicitar_serial_number(sock, device_id, addr)
                # envioScript(sock, device_id, addr)
            blocos_de_dados = Arquivos(device_id)
        if ip_equipamento not in equipamentos_executados:
            for bloco in blocos_de_dados:
                    # await enviar_bloco(sock, bloco, addr)
                fw=Firmware(device_id=device_id,SN=RSN_DICT[device_id],content_blocs=bloco)
                enviar_mensagem_udp(sock, addr, bloco)
            equipamentos_executados[ip_equipamento] = True
            print(equipamentos_executados)

            # equipamentos_executados[ip_equipamento] = True
        print('Mensagem recebida:', data)




if __name__ == "__main__":
    try:
        pasta_vozes = "./app/Files/Vozes/"
        pasta_scripts = "./app/Files/Prod_script/"
        path_voz = find(pasta_vozes)
        # print("Arquivos de Voz:",path_voz)
        path = []
        path_script = find(pasta_scripts)
        # print("Script basico:",path_script)
        if path_voz:
            asyncio.run(main())
            # servidor_udp()
    except KeyboardInterrupt:
        pass




