import socket
import XVM
import re
import psycopg2
import os
import time
import asyncio
import selectors
import time
from tenacity import retry, stop_after_delay, wait_fixed, stop_after_attempt, TryAgain
from sqlalchemy import create_engine, Column, String, LargeBinary, DateTime, func, select
from sqlalchemy.orm import sessionmaker,declarative_base
from datetime import datetime

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

# novo_firmware = Firmware(
#     device_id='id_do_dispositivo',
#     SN='numero_de_serie',
#     content_blocs=b'conteudo_blocos', 
#     blocs_acks=b'acks_dos_blocos',    
#     send_datetime=datetime.now(),
#     reception_datetime=datetime.now()
# )

# session.add(novo_firmware)
# session.commit()


def Arquivos(device_id):
        print(device_id)
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
                    b = bytes.fromhex(bloc)
                    BLOCOS.append(b)
                    if i == 0:
                        session.query(Firmware).filter_by(device_id=device_id).update(
                            {"SN": sn , "content_blocs": b, "inserted_datetime": datetime.now()}
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
            print(sn)
            LISTENED.append(device_id)
            RSN_DICT[device_id] = sn

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def enviar_mensagem_udp(sock, addr, mensagem):
    timeout = 5
    if isinstance(mensagem, bytes):
        sock.sendto(mensagem, addr)
    else:
        print(mensagem)
        sock.sendto(mensagem.encode(), addr)
    start_time = time.time()
    response, _ = sock.recvfrom(1024)
    print(response)
    if re.search(b'RUV.*',response) or re.search(b'.*NAK.*',response):
        send_ack(sock, addr, response)
        raise TryAgain
    if time.time() - start_time >= timeout:
        print("timeout")
        raise TryAgain
    return response

def send_ack(sock, addr, message):
    if re.search(b'BINA.*',message) is None:
        xvmMessage = XVM.parseXVM(message.decode(errors='ignore'))
        device_id = xvmMessage[1]
        sequence = xvmMessage[2]
        ack = XVM.generateAck(device_id,sequence)
        sock.sendto(ack.encode(), addr)
        print('ack enviado')
        return device_id

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

async def Verifica_ID():
    stmt = (
        select(Firmware)
        .where(
        # (Firmware.device_id is not None)
        #  & 
        (Firmware.SN == None))
    )
        
    result = session.execute(stmt)
    ids = [row.device_id for row in result.scalars()]
    if len(ids) == 0:
        print('Todos os dispositivos estão atualizados')
        await asyncio.sleep(60)
    print(ids)
    return ids


async def sending_bytes(sock, device_id, addr,blocos_de_dados):
    for bloco in blocos_de_dados:
        session.query(Firmware).filter_by(device_id=device_id,content_blocs=bloco).update(
            {"send_datetime": datetime.now()}
        )
        session.commit()
        res = await enviar_mensagem_udp(sock, addr, bloco)
        if res:
            session.query(Firmware).filter_by(device_id=device_id,content_blocs=bloco).update(
            {"blocs_acks":res,"reception_datetime": datetime.now()}
            )
        await asyncio.sleep(0.3)
    

async def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, porta))
    sock.settimeout(5)
    # sock.setblocking(False)
    print((host, porta))
    while True:
        try:
            ids_desatualizados = await Verifica_ID()
            data, addr = sock.recvfrom(1024)
            ip_equipamento = addr[0]
            print(data,ip_equipamento)
            print('Mensagem recebida:', data)
            # if ip_equipamento not in equipamentos_executados:
            # if re.search(b'BINA.*',data) is None:
            #     xvmMessage = XVM.parseXVM(data.decode(errors='ignore'))
            #     device_id = xvmMessage[1]
            device_id = send_ack(sock, addr, data)
            if device_id in ids_desatualizados:
                solicitar_serial_number(sock, device_id, addr)
                    # envioScript(sock, device_id, addr)
                print(RSN_DICT)
                blocos_de_dados = Arquivos(device_id)
            if device_id in RSN_DICT:
                blocos_de_dados= await Verifica_tabela(device_id)
            if ip_equipamento not in equipamentos_executados:
                # await enviar_bloco(sock, bloco, addr)
                await sending_bytes(sock, device_id, addr, blocos_de_dados)
                equipamentos_executados[ip_equipamento] = True
                print(equipamentos_executados)
        except socket.timeout:
            pass
        except KeyboardInterrupt:
            print("CRLT + C")
            exit()
        # finally:
            # await Verifica_tabela('teste')
        

if __name__ == "__main__":
    try:
        # pasta_vozes = "./app/Files/Vozes/"
        pasta_fw = "./app/Files/"
        path_fw = find(pasta_fw)
        # print("Arquivos de Voz:",path_voz)
        # path = []
        # path_script = find(pasta_scripts)
        # print("Script basico:",path_script)
        # if path_voz:
        fw = Firmware()
        asyncio.run(main())
            # servidor_udp()
    except KeyboardInterrupt:
        print("Finalizando")
        exit()




