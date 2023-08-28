import pytest
from app.FOTA import Verifica_tabela , Verifica_ID
from unittest.mock import Mock, mock_open, patch
from unittest import mock
import sys
import os
import re

# sys.path.append('./Envio-Firmware/app/')
# sys.path.append(os.path.join(os.path.dirname(sys.path[0]),'app'))
# @mock.patch('app.FOTA.verifica_ID.session.execute')
# def test_verifica_tabela_deve_retornar_a_lista_de_id_que_tem_todos_outros_campos_null():

#     ids  = []
#     if len(ids) != 0:
#         assert ids == [] 
#     assert ids == None
     

def test_regex():
    s = b'BINAVRFB"\xff\xff\xff_ACK08L32641\x80\x00\x00\x00\xeb\xab\xcc\xb5'
    s = b'BINAVRFB\x00\x12\x00\x08_ACK08L32641\x80\x00\x00\n\xc9F3H'
    r = b'\x81\x00\x00\x00\xeb\xab\xcc\xb5'
    if re.search(b'\x80\x00.*', s):
        teste2 = s.hex()
        teste = re.search('8000.{4}', teste2)
        assert teste == teste2
        if re.search(b'\n', teste):
            teste = re.sub(b'\n',b'',teste)
            assert teste == re.search(b'\x80\x00.{2}', s).group()
    else:
        assert False == True



