#!/usr/bin/env python3
# BlueKitchen GmbH (c) 2019

# pip3 install pycryptodomex

# implementation of the Bluetooth SIG Mesh crypto functions using pycryptodomex

from Cryptodome.Cipher import AES
from Cryptodome.Hash   import CMAC

def aes128(key, n):
    cipher = AES.new(key, AES.MODE_ECB)
    ciphertext = cipher.encrypt(n)
    return ciphertext

def aes_cmac(key, n):
    cobj = CMAC.new(key, ciphermod=AES)
    cobj.update(n)
    return cobj.digest()

def aes_ccm_encrypt(key, nonce, message, additional_data, mac_len):
    cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=mac_len)
    cipher.update(additional_data)
    ciphertext, tag = cipher.encrypt_and_digest(message)
    return ciphertext, tag

def aes_ccm_decrypt(key, nonce, message, additional_data, mac_len, mac_tag):
    cipher = AES.new(key, AES.MODE_CCM, nonce=nonce, mac_len=mac_len)
    cipher.update(additional_data)
    try:
        ciphertext = cipher.decrypt_and_verify(message, mac_tag)
        return ciphertext
    except ValueError:
        return None

def s1(m):
    # s1(M) = AES-CMACZERO (M)
    zero_key = bytes(16)
    return aes_cmac(zero_key, m)

def k1(n, salt, p):
    # T = AES-CMACSALT (N)
    t = aes_cmac(salt, n)
    # k1(N, SALT, P) = AES-CMACT (P)
    return aes_cmac(t, p)

def k2(n, p):
    # SALT = s1(“smk2”)
    salt = s1(b'smk2')
    # T = AES-CMACSALT (N)
    t = aes_cmac(salt, n)
    # T0 = empty string (zero length) 
    t0 = b''
    # T1 = AES-CMACT (T0 || P || 0x01)
    t1 = aes_cmac(t, t0 + p + b'\x01')
    # T2 = AES-CMACT (T1 || P || 0x02) 
    t2 = aes_cmac(t, t1 + p + b'\x02')
    # T3 = AES-CMACT (T2 || P || 0x03)
    t3 = aes_cmac(t, t2 + p + b'\x03')
    nid = t1[15] & 0x7f
    encryption_key = t2
    privacy_key = t3
    return (nid, encryption_key, privacy_key)

def k3(n):
    # SALT = s1(“smk3”)
    salt = s1(b'smk3')
    # T = AES-CMACSALT (N)
    t = aes_cmac(salt, n)
    return aes_cmac(t, b'id64' + b'\x01')[8:]

def k4(n):
    # SALT = s1(“smk4”)
    salt = s1(b'smk4')
    # T = AES-CMACSALT (N)
    t = aes_cmac(salt, n)
    return aes_cmac(t, b'id6' + b'\x01')[15] & 0x3f

def network_pecb(network_pdu, iv_index, privacy_key):
    privacy_random = network_pdu[7:14]
    privacy_plaintext = bytes(5) + iv_index + privacy_random
    return aes128(privacy_key, privacy_plaintext)[0:6]

def network_decrypt(network_pdu, iv_index, encryption_key, privacy_key):
    pecb = network_pecb(network_pdu, iv_index, privacy_key)
    deobfuscated = bytes([(a ^ b) for (a,b) in zip(pecb, network_pdu[1:7])])
    nonce = bytes(1) + deobfuscated + bytes(2) + iv_index
    decrypted = aes_ccm_decrypt(encryption_key, nonce, network_pdu[7:-8], b'', 8, network_pdu[-8:])
    return network_pdu[0:1] + deobfuscated + decrypted

