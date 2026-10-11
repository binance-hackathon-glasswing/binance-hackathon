"""Legacy EVM signing with exact-byte verification and an injected durable registry.

Registry must implement lookup(attempt_id,payload_hash), check_authority(epoch,version), and
put_if_absent(attempt_id,payload_hash,signed,epoch,version) atomically under current fencing.
Production registry implementation belongs to Keegan; no SQLite/file fallback is provided.
"""
from dataclasses import asdict
from larp.execution import Blocked, Signed, address, validate_payload


def verify(payload,signed):
    from eth_account import Account
    from eth_utils import keccak
    import rlp
    try:
        raw=bytes.fromhex(signed.raw_hex.removeprefix('0x'))
        fields=rlp.decode(raw,strict=True)
        if len(fields)!=9 or any(not isinstance(f,bytes) for f in fields) or rlp.encode(fields)!=raw:
            return False
        nums=[int.from_bytes(fields[i],'big') for i in (0,1,2,4,6)]
        if any(fields[i] and fields[i][0]==0 for i in (0,1,2,4,6,7,8)):return False
        nonce,price,gas,value,v=nums
        return (nonce==payload.nonce and price==payload.gas_price and gas==payload.gas and value==payload.value
                and v>=35 and (v-35)//2==payload.chain_id and '0x'+fields[3].hex()==payload.to
                and '0x'+fields[5].hex()==payload.data.lower()
                and Account.recover_transaction(raw).lower()==payload.sender
                and '0x'+keccak(raw).hex()==signed.tx_hash.lower())
    except (ValueError,TypeError,IndexError,rlp.exceptions.RLPException):
        return False


class LocalSigner:
    mode='live'
    def __init__(self,*,account,expected_address,registry,authorization,signer_host=False):
        if not signer_host or account.address.lower()!=address(expected_address.lower()):
            raise Blocked('isolated signer host and wallet binding required')
        if not all(callable(getattr(registry,k,None)) for k in ('lookup','check_authority','put_if_absent')):
            raise Blocked('durable fenced signer registry required')
        self.account,self.registry,self.authorization=account,registry,authorization

    @classmethod
    def from_secret_store(cls,secrets,**kwargs):
        from eth_account import Account
        key=secrets.get('WALLET_PRIVATE_KEY');mnemonic=secrets.get('WALLET_MNEMONIC')
        if bool(key)==bool(mnemonic):raise Blocked('exactly one signer credential required')
        if mnemonic:
            Account.enable_unaudited_hdwallet_features()
            account=Account.from_mnemonic(mnemonic)
        else:account=Account.from_key(key)
        return cls(account=account,expected_address=secrets['AI_SEEDS_ADDRESS'],**kwargs)

    def sign(self,attempt_id,payload,epoch,guard_version):
        self.registry.check_authority(epoch,guard_version)
        # Authorization returns the actual intent, step, current gates, trusted clock and verified decoder.
        intent,step,gates,now,decoder=self.authorization(attempt_id,payload,epoch,guard_version)
        if gates.epoch!=epoch or gates.state_version!=guard_version:raise Blocked('stale signer authority')
        validate_payload(intent,step,payload,gates,now,decoder)
        if payload.sender!=self.account.address.lower():raise Blocked('signer sender mismatch')
        stored=self.lookup(attempt_id,payload.hash)
        if stored is not None:
            if not verify(payload,stored):raise Blocked('stored signature mismatch')
            return stored
        from eth_utils import to_checksum_address
        tx=dict(chainId=payload.chain_id,nonce=payload.nonce,gasPrice=payload.gas_price,
                gas=payload.gas,to=to_checksum_address(payload.to),value=payload.value,data=payload.data)
        signed=self.account.sign_transaction(tx)
        result=Signed('0x'+signed.raw_transaction.hex(),'0x'+signed.hash.hex())
        if not verify(payload,result):raise Blocked('signed bytes do not match authorized payload')
        # Registry commits immutable bytes before any caller receives them; a lost CAS never releases bytes.
        stored=self.registry.put_if_absent(attempt_id,payload.hash,result,epoch,guard_version)
        if not verify(payload,stored):raise Blocked('registry signature mismatch')
        return stored

    def verify(self,payload,signed):return verify(payload,signed)
    def lookup(self,attempt_id,payload_hash):return self.registry.lookup(attempt_id,payload_hash)
