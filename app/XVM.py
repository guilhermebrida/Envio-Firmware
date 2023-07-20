
def calcCheckSum (msg):
    num = msg.find(';*')+1
    calc = 0
    for i in range(num): calc ^= ord(msg[i])
    return calc

def parseXVM(msg):
    xvmMessage=msg.split(';')  
    message  = xvmMessage[0]
    id       = xvmMessage[1][3:]
    sequence = int(xvmMessage[2][1:],16)
    checksum = int(xvmMessage[3][1:3],16)
    return (message,id,sequence,checksum)      

def generateAck(id,sequence):
    resp = '>ACK;ID='+id+';#'+format(sequence,'04X')+';*'
    resp = resp+format(calcCheckSum(resp),'02X')+'<\r\n'
    return resp

def generateXVM(id,sequence,message):
    resp = message+';ID='+id+';#'+sequence+';*'
    resp = resp+format(calcCheckSum(resp),'02X')+'<\r\n'
    return resp

def isValidXVM(msg):
    return 1 if calcCheckSum(msg)==parseXVM(msg)[3] else 0





