import socket
import re
import psycopg2
import os
import time
import asyncio
import selectors
import time
from tenacity import retry, stop_after_delay, wait_fixed, stop_after_attempt, TryAgain, RetryError
from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, func, select
from sqlalchemy.orm import sessionmaker,declarative_base
from datetime import datetime
from threading import Thread, Lock
import threading
import sys
sys.path.append('./app/')
diretorio_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..")) 
sys.path.append(diretorio_projeto)
import app.XVM as XVM
import tenacity

ips = []
RSN_DICT = {}
cabeçalho =  'BINAVSFB'
bloc =''
bloco =[]
path = []
blocos_envio = []
arquivos = None
BLOCOS = []
LISTENED = []
device_id = None
addr = None

postgres_host = os.environ['POSTGRES_HOST']
postgres_port = os.environ['POSTGRES_PORT']
postgres_user = os.environ['POSTGRES_USER']
postgres_password = os.environ['POSTGRES_PASSWORD']
postgres_db = os.environ['POSTGRES_DB']

# connection = psycopg2.connect(
#     host=postgres_host,
#     # host="postgres",
#     port=postgres_port,
#     user=postgres_user,
#     password=postgres_password,
#     dbname=postgres_db
# )

# cursor = connection.cursor()




host = '0.0.0.0'
porta = 10116
equipamentos_executados = {}
blocos_de_dados = [...]  




# engine = create_engine('postgresql://postgres:postgres@localhost:5432/postgres')
engine = create_engine(f'postgresql://{postgres_user}:{postgres_password}@{postgres_host}:{postgres_port}/{postgres_db}')
Base = declarative_base()

class Firmware(Base):
    __tablename__ = 'firmware'

    device_id = Column(String, primary_key=True)
    SN = Column(String, default=None)
    content_blocs = Column(LargeBinary)
    blocs_acks = Column(LargeBinary)
    inserted_datetime = Column(DateTime, default=None)
    send_datetime = Column(DateTime, default=None)
    reception_datetime = Column(DateTime, default=None)

    def __repr__(self):
        return f"Firmware(device_id={self.device_id}, SN={self.SN}, blocs_content={self.content_blocs})"



Session = sessionmaker(bind=engine, autoflush=True )
session = Session()

def Arquivos(device_id):
        print("===================================================================================")
        print("== Arquivos()")
        print(f"devicd_id={device_id}")
        sn = RSN_DICT[device_id]
        # print(path_voz)
        for files in path_fw:
            with open(files, 'rb') as f:
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
                    print(msg)
                    b = bytes.fromhex(bloc)
                    BLOCOS.append(b)
                    if i == 0:
                        session.query(Firmware).filter_by(device_id=device_id).update(
                            {"SN": sn , "content_blocs": b, "inserted_datetime": datetime.now(), "bloc_sequence":msg}
                            )
                    else:
                        fw=Firmware(device_id=device_id,SN=RSN_DICT[device_id],content_blocs=b, inserted_datetime=datetime.now())
                        session.add(fw)
                    session.commit()
        print('return')
        # print(BLOCOS)
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


def solicitar_serial_number():
    global device_id
    global addr
    print("===================================================================================")
    print("== solicitar_serial_number()")
    xvm = XVM.generateXVM(device_id, str(8000).zfill(4), '>QSN<')
    print(xvm)
    enviar_mensagem_udp(sock,addr,xvm)
    # result = re.search('>RSN.*', response.decode())
    # if result is not None:
    #     rsn = result.group()
    #     sn = rsn.split('_')[0].split('>RSN')[1]
    #     if sn:
    #         print(sn)
    #         RSN_DICT[device_id] = sn

@retry(stop=stop_after_attempt(5), wait=wait_fixed(3))
def enviar_mensagem_udp(sock, addr, mensagem):
    # try:
        print("===================================================================================")
        print("== enviar_mensagem_udp()")
        timeout = 5
        if isinstance(mensagem, bytes):
            print(f'{datetime.now().strftime("%d/%m/%Y, %H:%M:%S")} {mensagem[:30]}')
            sock.sendto(mensagem, addr)
        else:
            print(f'{datetime.now().strftime("%d/%m/%Y, %H:%M:%S")} {mensagem[:30]}')
            sock.sendto(mensagem.encode(), addr)
        start_time = time.time() 
        # response, _ = sock.recvfrom(1024)

def recever_msg():
    global device_id
    global addr
    while True:
        print("===================================================================================")
        print("== recever_msg()")
        response,addr = sock.recvfrom(1024)
        ip_equipamento = addr[0]
        print(response,ip_equipamento)
        print(f'{datetime.now().strftime("%d/%m/%Y, %H:%M:%S")} {response}')
        if re.search(b'RUV.*',response) or re.search(b'.*NAK.*',response):
            send_ack(sock, addr, response)
        result = re.search('>RSN.*', response.decode())
        if result is not None:
            rsn = result.group()
            sn = rsn.split('_')[0].split('>RSN')[1]
            if sn:
                print(f'device_id={device_id}')
                print(f"SN={sn}")
                RSN_DICT[device_id] = sn
        # if re.search(b'BINA.*ACK.*',response):
            # session.query(Firmware).filter_by(device_id=device_id,content_blocs=bloco).update(
            # {"blocs_acks":response,"reception_datetime": datetime.now()}
            # )
            # session.commit()

            # raise TryAgain
        # if time.time() - start_time >= timeout:
        #     print("timeout")
        #     raise TryAgain
        # return response
    # except RetryError:
    #     print('RETRY ERRO NA ENVIAR MSG UDP')
    #     pass





def send_ack(sock, addr, message):
    global device_id
    if re.search(b'BINA.*',message) is None:
        xvmMessage = XVM.parseXVM(message.decode(errors='ignore'))
        device_id = xvmMessage[1]
        sequence = xvmMessage[2]
        ack = XVM.generateAck(device_id,sequence)
        print(device_id)
        print(ack)
        sock.sendto(ack.encode(), addr)
        # return device_id

async def Verifica_tabela(device_id):
    blocos = []
    stmt = (
        select(Firmware.content_blocs)
        .where(
        # (Firmware.device_id == device_id)&
        (Firmware.blocs_acks == None))
    )
    
    result = session.execute(stmt)
    
    for row in result.scalars():
        blocos.append(row)
    # print(blocos)
    return blocos

def Verifica_ID():
    stmt = (
        select(Firmware)
        .where(
        # (Firmware.device_id is not None)
        #  & 
        (Firmware.SN == None))
    )
    result = session.execute(stmt)
    ids = [row.device_id for row in result.scalars()]
    if len(ids) != 0:
        print(ids)
        return ids
    print('Todos os dispositivos estão atualizados')
    return None



def periodic_query(ids_desatualizados:list):
    while True:
        ids = Verifica_ID()
        if ids is not None:
            for id in ids:
                if id not in ids_desatualizados:
                    ids_desatualizados.append(id)
        # print(ids_desatualizados)
        time.sleep(10)


# @retry(stop=stop_after_attempt(10), wait=wait_fixed(3))
def sending_bytes(device_id, addr,blocos_de_dados):
    try:
        for bloco in blocos_de_dados:
            session.query(Firmware).filter_by(device_id=device_id,content_blocs=bloco).update(
                {"send_datetime": datetime.now()}
            )
            session.commit()
            res = enviar_mensagem_udp(sock, addr, bloco)
            # if re.search(b'.ACK.*',res):
            #     session.query(Firmware).filter_by(device_id=device_id,content_blocs=bloco).update(
            #     {"blocs_acks":res,"reception_datetime": datetime.now()}
            #     )
            #     session.commit()
        print('atualizado!')
        return True
        # else:
        #     raise TryAgain
        # if RetryError:
        #     reload_table(device_id)
    except RetryError as e:
        print('RETRY ERRO NA SENDING_BYTES',e)
        reload_table(device_id)

        # time.sleep(0.3)

def reload_table(device_id):
    stmt = (
        select(Firmware.content_blocs)
        .where(
        (Firmware.device_id == device_id)&
        (Firmware.blocs_acks != None))
    )
    result = session.execute(stmt)
    acks = [row for row in result.scalars()]
    print(len(acks))
    for ack in acks:
        session.query(Firmware).filter_by(device_id=device_id,blocs_acks=ack).update(
            {"blocs_acks":None, "send_datetime": None, "reception_datetime": None}
        )
        session.commit()


def contador():
    count = 0
    while True:
        # print("Contador:", count)
        count += 1
        time.sleep(1)

async def main():
    global device_id
    global addr
    print((host, porta))
    ids_desatualizados = []
    thread = Thread(target=periodic_query, args=(ids_desatualizados,))
    thread.start()
    Thread(target=recever_msg).start()
    try :
        while True:
            # data, addr = sock.recvfrom(1024)
            
            # device_id = send_ack(sock)
            # lista_ids = list({item for sublist in ids_desatualizados for item in sublist if item != []})
            # print('LISTA IDS:',lista_ids)
            # print('LISTENED:',LISTENED)
            print("===================================================================================")
            print("== main()")
            print(device_id)
            if device_id in ids_desatualizados:
                print(device_id, ids_desatualizados[0])
                print(device_id in ids_desatualizados[0])
                solicitar_serial_number()
                print(f'RSN_DICT={RSN_DICT}')
            if device_id in RSN_DICT:
                blocos_de_dados = Arquivos(device_id)
                blocos_de_dados= await Verifica_tabela(device_id)
                # if ip_equipamento not in equipamentos_executados:
                    # await enviar_bloco(sock, bloco, addr)
                    # thread2 = Thread(target=sending_bytes, args=(device_id, addr, blocos_de_dados))
                    # thread2.start()
                    # thread2.join()
                # threading.Thread(target=contador, daemon=True).start()
                sending_bytes(device_id, addr, blocos_de_dados)
                LISTENED.append(device_id)
                print(f'FAZENDO APPEND {LISTENED}')
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("CRLT + C")            
            # await Verifica_tabela('teste')


if __name__ == "__main__":
    try:

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((host, porta))
        # sock.setblocking(False)
        # sock.settimeout(60)
        pasta_fw = "./app/Files/"
        path_fw = find(pasta_fw)
        fw = Firmware()
        asyncio.run(main())
            # servidor_udp()
    except KeyboardInterrupt:
        print("Finalizando")
    # except socket.timeout:
        # pass
    # finally:
    #     sock.shutdown(socket.SHUT_RDWR)
    #     sock.close()
    #     exit()
