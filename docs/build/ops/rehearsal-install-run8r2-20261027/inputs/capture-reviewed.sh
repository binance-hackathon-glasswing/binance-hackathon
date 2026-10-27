set -eu
cd /opt/larp/current
env PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B - <<'PY'

def exit_children(whole, proceeds, cap_raw, limit):
    children, remaining = [], whole
    while remaining and len(children) < limit:
        value = proceeds * remaining
        parts = max(1, -(-value * 10100 // (whole * 10000 * cap_raw)))
        children.append(remaining if parts == 1 else remaining // parts)
        remaining -= children[-1]
    return children + ([remaining] if remaining else [])
SELECTED_PROFILE_B64 = 'eyJhc3Nlc3NtZW50X3JlcXVpcmVkIjpmYWxzZSwiYmFzZWxpbmUiOiJUUkVORF9HVUFSREVEX1ZPTCIsImNvc3RfcmVzZXJ2ZV91bml0cyI6MTAwMDAwLCJkdXN0X3VuaXRzIjowLCJlbnRyeV9jb3N0X2Jhc2lzIjoiQVVUSE9SSVpFRF9NSU5JTVVNIiwiZW52aXJvbm1lbnQiOiJSRUhFQVJTQUwiLCJldmlkZW5jZV9tYXhfYWdlX21zIjozNjAwMDAwLCJldmlkZW5jZV9tb2RlIjoiQk9VTkRFRF9GQUxTSUZJRVIiLCJleGVjdXRpb25fYXV0aG9yaXR5X3NlY29uZHMiOjY2MCwiZXhpdF9nYXNfcmVzZXJ2ZV91bml0cyI6MTUzNjAwMDAwMDAwMDAwMDAsImV4cGVjdGVkX2VxdWl0eV91bml0cyI6MTAwMDAwMDAwLCJmYWxzaWZpZXJfYXV0aG9yaXR5IjoiRElTQ1JFVElPTkFSWV9FWElUIiwiZmFsc2lmaWVyX2lkcyI6WyJGLUlURU0tNC4wMiIsIkYtSVRFTS0xLjA1IiwiRi1JVEVNLTIuMDYiXSwiZmVhdHVyZV9hZ2Vfc2Vjb25kcyI6MzQ1NjAwLCJmbGF0dGVuX3N0YXJ0IjoiMjAyNi0xMC0yN1QxNTowMDowMFoiLCJnYXNfYWN0aW9uX2J1ZGdldF91bml0cyI6MTUzNjAwMDAwMDAwMDAwMCwiZ2FzX3NpemluZ19idWRnZXRfdW5pdHMiOjgwMDA0NjA4MDAwMDAwLCJpbXBhY3RfYnBzIjoyLCJpbXBhY3RfbWVkaWFuX2JwcyI6eyJHT09HTEIiOjEsIk1TRlRCIjoxLCJOVkRBQiI6MSwiU0tIWUIiOjEsIlRTTEFCIjoxfSwiaW5pdGlhbF9nYXNfb25seSI6dHJ1ZSwibWluaW11bV9yZW1haW5pbmdfc2Vzc2lvbnMiOjAsIm1pbmltdW1fdHJhZGVfdW5pdHMiOjMxOTIwNDUsIm1vZGUiOiJMSVZFIiwibmV3X3Jpc2tfZW5kIjoiMjAyNi0xMC0yN1QxNDowMDowMFoiLCJwZXJfdHJhZGVfY2FwX3VuaXRzIjoxOTEwMDAwMCwicG9saWN5X2lkIjoibGFycC1zNS1yZWhlYXJzYWwtdjEiLCJwcmVkaWNhdGVfcmVnaXN0cnlfaGFzaCI6ImRmMWUyZWI2OWFlNTA3ZjE0ZDcwNjgzYTBlYTcxZDQ4NzRlZDc5MzE2MWE0NjZhMjQ3ODZlM2YxZjZkYTE5ZTIiLCJwcmljZV90aHJlc2hvbGRfYnBzIjowLCJwcm9wb3NhbF9zZWNvbmRzIjoxNSwicHJvdmVuYW5jZSI6eyJhc3Nlc3NtZW50X3JlcXVpcmVkIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJGcm96ZW4gQjYgcG9saWN5IGJ1ZGdldDsgc2VlIGNvbmZpZy9zdHJhdGVneS9MSVZFLm1kIGFuZCBJREVBLTA0MCJ9LCJiYXNlbGluZSI6eyJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1LU5FWFQwMSAoS2VlZ2FuLCAyMDI2LTEwLTI3KSIsImZvcm11bGEiOiJJREVBLTA3NSDCpzQtwqc1LCDCpzEyIHZhbHVlczsgd2VpZ2h0cyBmcm9tIHMxIGZyZWV6ZS13ZWlnaHRzIn0sImNvc3RfcmVzZXJ2ZV91bml0cyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiY2VpbChleHBlY3RlZF9lcXVpdHlfdW5pdHMvMTAwMCk6IDUwIGJwIG9mIDIwJSBwb3NpdGlvbiJ9LCJkdXN0X3VuaXRzIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJGcm96ZW4gQjYgcG9saWN5IGJ1ZGdldDsgc2VlIGNvbmZpZy9zdHJhdGVneS9MSVZFLm1kIGFuZCBJREVBLTA0MCJ9LCJlbnRyeV9jb3N0X2Jhc2lzIjp7ImRlY2lzaW9uX2lkIjoiSURFQS0xMDQgUzUtU01BTEwwMSAoWWFvIHJlcXVlc3QsIDIwMjYtMTAtMjcpIiwiZm9ybXVsYSI6IkF1dGhvcml6ZWQgbWluaW11bSBvdXRwdXQgcGx1cyBmZWVzIGFuZCBleHBlY3RlZCBnYXM7IFM1IDIwMGJwLCBleGlzdGluZyBjb3N0IHJlc2VydmUgYXBwbGllcyJ9LCJlbnZpcm9ubWVudCI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiRnJvemVuIEI2IHBvbGljeSBidWRnZXQ7IHNlZSBjb25maWcvc3RyYXRlZ3kvTElWRS5tZCBhbmQgSURFQS0wNDAifSwiZXZpZGVuY2VfbWF4X2FnZV9tcyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiRnJvemVuIEI2IHBvbGljeSBidWRnZXQ7IHNlZSBjb25maWcvc3RyYXRlZ3kvTElWRS5tZCBhbmQgSURFQS0wNDAifSwiZXZpZGVuY2VfbW9kZSI6eyJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1IFIzICh0ZWFtIHJlcXVlc3QsIDIwMjYtMTAtMjYpIiwiZm9ybXVsYSI6IkZTMSBGSU5BTCB2MSBzY29wZTogcm91dGVkIEFJYW5kL0NoYXRHUFQgYXNzZXNzbWVudCwgdmVyaWZpZWQgcmVkIGZsYWdzIGV4aXQgb3IgYmxvY2sgZW50cnk7IG5lZWRzIHJldmlld2VkIHJvdXRpbmcgKG5vIGRldGVybWluaXN0aWMgc2lnbmluZykifSwiZXhlY3V0aW9uX2F1dGhvcml0eV9zZWNvbmRzIjp7ImRhdGFfaGFzaCI6ImFkNDNiNjM0NjU0MmYxNTdjODRmYTExM2I2ODAyZjZiZmNlNmM2YWFkMWQ1MzkzNjgwYmM3YWMyNGJjNGNlZDQiLCJkZWNpc2lvbl9pZCI6IklERUEtMDQ5LUMgTEQwNC1WMDEgKEtlZWdhbiwgMjAyNi0xMC0yMCkifSwiZXhpdF9nYXNfcmVzZXJ2ZV91bml0cyI6eyJkYXRhX2hhc2giOiIwNDlkOTgzMzcwMTlkNjU3OTE2MjUwNDA2N2ZkZjI2ZTMzYTY1ZTU3YmM3NzEwYWRkOTg3OTdiNmJkOGUxOGVmIiwiZGVjaXNpb25faWQiOiJJREVBLTA5OCAoSURFQS0wOTYgRjIvRjMgcmVjb3ZlcnkgZ2FzIGF0IHRoZSBDQVAtMDIgY2VpbGluZ3MpIiwiZm9ybXVsYSI6IjUgcG9zaXRpb25zKjIgYmFsYW5jZWQgZXhpdCBjaGlsZHJlbipnYXNfYWN0aW9uX2J1ZGdldF91bml0cyJ9LCJleHBlY3RlZF9lcXVpdHlfdW5pdHMiOnsiZGF0YV9oYXNoIjoiMDNiZWNjMDgxNzBmOWQ2YzVkZDg4MjZmNjFkOTZmNTMwNjcwMDA1OGNhM2RjYTAwZGYzZWI0MTNmYWY5ZjU0MyIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjYgLyBJREVBLTAzNyAvIElERUEtMDQwIiwiZm9ybXVsYSI6IkZyb3plbiBCNiBwb2xpY3kgYnVkZ2V0OyBzZWUgY29uZmlnL3N0cmF0ZWd5L0xJVkUubWQgYW5kIElERUEtMDQwIn0sImZhbHNpZmllcl9hdXRob3JpdHkiOnsiZGVjaXNpb25faWQiOiJJREVBLTEwNCBTNSBSMyAodGVhbSByZXF1ZXN0LCAyMDI2LTEwLTI2KSIsImZvcm11bGEiOiJGUzEgRklOQUwgdjEgc2NvcGU6IHJvdXRlZCBBSWFuZC9DaGF0R1BUIGFzc2Vzc21lbnQsIHZlcmlmaWVkIHJlZCBmbGFncyBleGl0IG9yIGJsb2NrIGVudHJ5OyBuZWVkcyByZXZpZXdlZCByb3V0aW5nIChubyBkZXRlcm1pbmlzdGljIHNpZ25pbmcpIn0sImZhbHNpZmllcl9pZHMiOnsiZGF0YV9oYXNoIjoiZGYxZTJlYjY5YWU1MDdmMTRkNzA2ODNhMGVhNzFkNDg3NGVkNzkzMTYxYTQ2NmEyNDc4NmUzZjFmNmRhMTllMiIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjEifSwiZmVhdHVyZV9hZ2Vfc2Vjb25kcyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiNCo4NjQwMDsgY2FsZW5kYXIgYWRqYWNlbmN5IHNlcGFyYXRlbHkgcmVxdWlyZWQifSwiZmxhdHRlbl9zdGFydCI6eyJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1LU5FWFQwMSAoS2VlZ2FuLCAyMDI2LTEwLTI3KSIsImZvcm11bGEiOiJTdGFydCB3aGVuIHF1YWxpZmllZDsgYnV5IGN1dG9mZjIyOjAwU0dULCBmbGF0dGVuMjM6MDBTR1QsIHNpZ25pbmcgZW5kIE9jdDI4IDAwOjAwU0dUIn0sImdhc19hY3Rpb25fYnVkZ2V0X3VuaXRzIjp7ImRhdGFfaGFzaCI6IjA0OWQ5ODMzNzAxOWQ2NTc5MTYyNTA0MDY3ZmRmMjZlMzNhNjVlNTdiYzc3MTBhZGQ5ODc5N2I2YmQ4ZTE4ZWYiLCJkZWNpc2lvbl9pZCI6IklERUEtMDk4IChJREVBLTA5NiBGMi9GMyByZWNvdmVyeSBnYXMgYXQgdGhlIENBUC0wMiBjZWlsaW5ncykiLCJmb3JtdWxhIjoiOCBjaGlsZHJlbiptYXhfZ2FzKm1heF9nYXNfcHJpY2U7IDw9NSBvdGhlci10b2tlbiByZXZva2VzICsgYXBwcm92ZSArIHN3YXAgb3IgYWJvcnQgcGF5LXRva2VuIHJldm9rZTsgb3JpZ2luYWwgYXV0aG9yaXR5IG9ubHkifSwiZ2FzX3NpemluZ19idWRnZXRfdW5pdHMiOnsiZGF0YV9oYXNoIjoiMDQ5ZDk4MzM3MDE5ZDY1NzkxNjI1MDQwNjdmZGYyNmUzM2E2NWU1N2JjNzcxMGFkZDk4Nzk3YjZiZDhlMThlZiIsImRlY2lzaW9uX2lkIjoiSURFQS0wOTggKElERUEtMDk2IEYyL0YzIHJlY292ZXJ5IGdhcyBhdCB0aGUgQ0FQLTAyIGNlaWxpbmdzKSIsImZvcm11bGEiOiJjbGVhbi1wYWlyIGV4cGVjdGVkIGdhczsgdmVyaWZpZXIgYWRkcyBvYnNlcnZlZCBvdGhlci10b2tlbiByZXZva2VzICpjZWlsKG1heCBtZWFzdXJlZCBhcHByb3ZlIGdhcyo1LzQpOyBhY3Rpb24gcmVzZXJ2ZXMgc2lnbmVkIG1heGltYSJ9LCJpbXBhY3RfYnBzIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJtaW4oNTAsbWF4X3N5bWJvbCgyKm1lZGlhbl9pbXBhY3RfYnBzKSkifSwiaW1wYWN0X21lZGlhbl9icHMiOnsiZGF0YV9oYXNoIjoiMDNiZWNjMDgxNzBmOWQ2YzVkZDg4MjZmNjFkOTZmNTMwNjcwMDA1OGNhM2RjYTAwZGYzZWI0MTNmYWY5ZjU0MyIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjYgLyBJREVBLTAzNyAvIElERUEtMDQwIiwiZm9ybXVsYSI6Im1lYXN1cmVkIG1lZGlhbiBwZXIgc3ltYm9sIGluIHBpbm5lZCBxdW90ZSBzdW1tYXJ5In0sImluaXRpYWxfZ2FzX29ubHkiOnsiZGVjaXNpb25faWQiOiJJREVBLTA2MSBMRDA3IiwiZm9ybXVsYSI6IkluaXRpYWwgZ2FzIG9ubHk7IG5vIGFnZW50IHRvcC11cHM7IG1lYXN1cmVkIHNlZWRpbmcgYW5kIHJlc2VydmUgYWNjZXB0YW5jZSBwZW5kaW5nIn0sIm1pbmltdW1fcmVtYWluaW5nX3Nlc3Npb25zIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJGcm96ZW4gQjYgcG9saWN5IGJ1ZGdldDsgc2VlIGNvbmZpZy9zdHJhdGVneS9MSVZFLm1kIGFuZCBJREVBLTA0MCJ9LCJtaW5pbXVtX3RyYWRlX3VuaXRzIjp7ImRhdGFfaGFzaCI6IjA0OWQ5ODMzNzAxOWQ2NTc5MTYyNTA0MDY3ZmRmMjZlMzNhNjVlNTdiYzc3MTBhZGQ5ODc5N2I2YmQ4ZTE4ZWYiLCJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1LVNNQUxMMDEgKFlhbyByZXF1ZXN0LCAyMDI2LTEwLTI3KSIsImZvcm11bGEiOiJtYXhfc3ltYm9sIGNlaWwoMTAwMDAqc2l6aW5nX2dhc192YWx1ZS8oMjAwLXNwcmVhZC1taW4oNTAsMiptZWRpYW5faW1wYWN0KS1mZWVfYnApKSJ9LCJuZXdfcmlza19lbmQiOnsiZGVjaXNpb25faWQiOiJJREVBLTEwNCBTNS1ORVhUMDEgKEtlZWdhbiwgMjAyNi0xMC0yNykiLCJmb3JtdWxhIjoiU3RhcnQgd2hlbiBxdWFsaWZpZWQ7IGJ1eSBjdXRvZmYyMjowMFNHVCwgZmxhdHRlbjIzOjAwU0dULCBzaWduaW5nIGVuZCBPY3QyOCAwMDowMFNHVCJ9LCJwZXJfdHJhZGVfY2FwX3VuaXRzIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJjZWlsKGV4cGVjdGVkX2VxdWl0eV91bml0cypzMS5oaWdoKm1heChzMS53ZWlnaHRzKSkgKyBjb3N0X3Jlc2VydmVfdW5pdHMifSwicG9saWN5X2lkIjp7ImRlY2lzaW9uX2lkIjoiSURFQS0xMDQgUzUtU01BTEwwMSAoWWFvIHJlcXVlc3QsIDIwMjYtMTAtMjcpIiwiZm9ybXVsYSI6IlNtYWxsLXdhbGxldCBGUzEgcmVoZWFyc2FsIHdpdGggcHJvcG9ydGlvbmFsIHRhcmdldHMgYW5kIHNjb3BlZDIwMGJwIGVudHJ5IGVjb25vbWljczsgZGV2IG9ubHkifSwicHJlZGljYXRlX3JlZ2lzdHJ5X2hhc2giOnsiZGF0YV9oYXNoIjoiZGYxZTJlYjY5YWU1MDdmMTRkNzA2ODNhMGVhNzFkNDg3NGVkNzkzMTYxYTQ2NmEyNDc4NmUzZjFmNmRhMTllMiIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjEifSwicHJpY2VfdGhyZXNob2xkX2JwcyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiRnJvemVuIEI2IHBvbGljeSBidWRnZXQ7IHNlZSBjb25maWcvc3RyYXRlZ3kvTElWRS5tZCBhbmQgSURFQS0wNDAifSwicHJvcG9zYWxfc2Vjb25kcyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoibWluKDE1LHF1b3RlX2FnZV9zZWNvbmRzKSJ9LCJxdW90ZV9hZ2Vfc2Vjb25kcyI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoibWluKDMwLG1pbl9zeW1ib2wgcXVvdGVfdHRsX3NlY29uZHMpIn0sInF1b3RlX2Nvc3Rfc3VtbWFyeSI6eyJkYXRhX2hhc2giOiIwM2JlY2MwODE3MGY5ZDZjNWRkODgyNmY2MWQ5NmY1MzA2NzAwMDU4Y2EzZGNhMDBkZjNlYjQxM2ZhZjlmNTQzIiwiZGVjaXNpb25faWQiOiJJREVBLTAzNSBCNiAvIElERUEtMDM3IC8gSURFQS0wNDAiLCJmb3JtdWxhIjoiRnJvemVuIEI2IHBvbGljeSBidWRnZXQ7IHNlZSBjb25maWcvc3RyYXRlZ3kvTElWRS5tZCBhbmQgSURFQS0wNDAifSwicmVkX2ZsYWdfYXV0aG9yaXR5Ijp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJGcm96ZW4gQjYgcG9saWN5IGJ1ZGdldDsgc2VlIGNvbmZpZy9zdHJhdGVneS9MSVZFLm1kIGFuZCBJREVBLTA0MCJ9LCJyZWRfZmxhZ19wb2xpY3kiOnsiZGF0YV9oYXNoIjoiZGYxZTJlYjY5YWU1MDdmMTRkNzA2ODNhMGVhNzFkNDg3NGVkNzkzMTYxYTQ2NmEyNDc4NmUzZjFmNmRhMTllMiIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjEifSwicmV2aWV3X3Nlc3Npb25zIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDM1IEI2IC8gSURFQS0wMzcgLyBJREVBLTA0MCIsImZvcm11bGEiOiJGcm96ZW4gQjYgcG9saWN5IGJ1ZGdldDsgc2VlIGNvbmZpZy9zdHJhdGVneS9MSVZFLm1kIGFuZCBJREVBLTA0MCJ9LCJydW5faGFsdF9yZWNvdmVyeV9icHMiOnsiZGVjaXNpb25faWQiOiJJREVBLTA4NCBQRi0wMjsgSURFQS0wOTMgUFIyNzgtUlYwMSIsImZvcm11bGEiOiJDbGVhciBvbmx5IHRoZSA4JSBidXkgc3RvcCBzdHJpY3RseSBiZWxvdyA1JSBkcmF3ZG93biB3aXRoIGZyZXNoIGNvbXBsZXRlIHJlY29uY2lsZWQgdmFsdWF0aW9uIn0sInMxIjp7ImRhdGFfaGFzaCI6IjM1ZTIwYzM4ZTIzNjU3ZGE2NzIzZTMxYjE4ZjMyM2U1ZjVlZGU3NzhkZTkzOGQ3M2M3MmZmMWEyYzE0MDhkMDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1LU5FWFQwMSAoS2VlZ2FuLCAyMDI2LTEwLTI3KSIsImZvcm11bGEiOiJJREVBLTA3NSDCpzQtwqc1LCDCpzEyIHZhbHVlczsgd2VpZ2h0cyBmcm9tIHMxIGZyZWV6ZS13ZWlnaHRzIn0sInMxX2NhcGl0YWxfYmFzaXMiOnsiZGVjaXNpb25faWQiOiJJREVBLTA5MyBQUjI3OC1SVjAxLUdBUzsgRi0xMjUgKHJldmlldyBjYW5kaWRhdGUpIiwiZm9ybXVsYSI6Ik5vbWluYWwgUzEgbGV2ZWxzIGFwcGx5IHRvIGNhc2ggcGx1cyBtYXJrZWQgc3RvY2tzIG1pbnVzIGNvc3QgcmVzZXJ2ZTsgbmF0aXZlIGdhcyBleGNsdWRlZCJ9LCJzMV9yZWR1Y3Rpb25fY29zdF9jYXBfYnBzIjp7ImRlY2lzaW9uX2lkIjoiSURFQS0wOTMgUFIyNzgtUlYwMSAocmV2aWV3IGNhbmRpZGF0ZSkiLCJmb3JtdWxhIjoiUGVuZGluZyBTMSBsZXZlbCBTRUxMIG1heSBiZSBiZWxvdyBlbnRyeSBtaW5pbXVtIG9ubHkgYXQgYXV0aG9yaXplZC1taW5pbXVtIGNvc3QgPD01MGJwIGFuZCBjb3N0IHJlc2VydmUifSwiczVfZW50cnlfY29zdF9jYXBfYnBzIjp7ImRlY2lzaW9uX2lkIjoiSURFQS0xMDQgUzUtU01BTEwwMSAoWWFvIHJlcXVlc3QsIDIwMjYtMTAtMjcpIiwiZm9ybXVsYSI6IlM1LW9ubHkgMjAwYnAgZW50cnktY29zdCBhbGxvd2FuY2UgZm9yIHByb3BvcnRpb25hbCBzbWFsbC13YWxsZXQgdGFyZ2V0czsgRlMxIHN0YXlzIDUwYnAifSwic2VyaWVzX2tpbmQiOnsiZGF0YV9oYXNoIjoiMDNiZWNjMDgxNzBmOWQ2YzVkZDg4MjZmNjFkOTZmNTMwNjcwMDA1OGNhM2RjYTAwZGYzZWI0MTNmYWY5ZjU0MyIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjYgLyBJREVBLTAzNyAvIElERUEtMDQwIiwiZm9ybXVsYSI6IkZyb3plbiBCNiBwb2xpY3kgYnVkZ2V0OyBzZWUgY29uZmlnL3N0cmF0ZWd5L0xJVkUubWQgYW5kIElERUEtMDQwIn0sInNpZ25pbmdfZW5kIjp7ImRlY2lzaW9uX2lkIjoiSURFQS0xMDQgUzUtTkVYVDAxIChLZWVnYW4sIDIwMjYtMTAtMjcpIiwiZm9ybXVsYSI6IlN0YXJ0IHdoZW4gcXVhbGlmaWVkOyBidXkgY3V0b2ZmMjI6MDBTR1QsIGZsYXR0ZW4yMzowMFNHVCwgc2lnbmluZyBlbmQgT2N0MjggMDA6MDBTR1QifSwic2xpcHBhZ2VfYnBzIjp7ImRhdGFfaGFzaCI6IjAzYmVjYzA4MTcwZjlkNmM1ZGQ4ODI2ZjYxZDk2ZjUzMDY3MDAwNThjYTNkY2EwMGRmM2ViNDEzZmFmOWY1NDMiLCJkZWNpc2lvbl9pZCI6IklERUEtMDkzIEZTMSIsImZvcm11bGEiOiIyMCBicCAoPD0gNTApLCB0aGUgRlMxIGZpbmFsIHZhbHVlIGFmdGVyIFMyLUY2IChJREVBLTA5MCBGMTYpIn0sInN0YXRlbWVudF9hdXRob3JpdHkiOnsiZGF0YV9oYXNoIjoiMDNiZWNjMDgxNzBmOWQ2YzVkZDg4MjZmNjFkOTZmNTMwNjcwMDA1OGNhM2RjYTAwZGYzZWI0MTNmYWY5ZjU0MyIsImRlY2lzaW9uX2lkIjoiSURFQS0wMzUgQjYgLyBJREVBLTAzNyAvIElERUEtMDQwIiwiZm9ybXVsYSI6IkZyb3plbiBCNiBwb2xpY3kgYnVkZ2V0OyBzZWUgY29uZmlnL3N0cmF0ZWd5L0xJVkUubWQgYW5kIElERUEtMDQwIn0sInN1Ym1pc3Npb25fbWFyZ2luX3NlY29uZHMiOnsiZGF0YV9oYXNoIjoiYWQ0M2I2MzQ2NTQyZjE1N2M4NGZhMTEzYjY4MDJmNmJmY2U2YzZhYWQxZDUzOTM2ODBiYzdhYzI0YmM0Y2VkNCIsImRlY2lzaW9uX2lkIjoiSURFQS0wNDktQyBMRDA0LVYwMSAoS2VlZ2FuLCAyMDI2LTEwLTIwKSJ9LCJ0cmFkZV9hZnRlciI6eyJkZWNpc2lvbl9pZCI6IklERUEtMTA0IFM1LU5FWFQwMSAoS2VlZ2FuLCAyMDI2LTEwLTI3KSIsImZvcm11bGEiOiJTdGFydCB3aGVuIHF1YWxpZmllZDsgYnV5IGN1dG9mZjIyOjAwU0dULCBmbGF0dGVuMjM6MDBTR1QsIHNpZ25pbmcgZW5kIE9jdDI4IDAwOjAwU0dUIn19LCJxdW90ZV9hZ2Vfc2Vjb25kcyI6MzAsInF1b3RlX2Nvc3Rfc3VtbWFyeSI6eyJibmJfZGVjaW1hbHMiOjE4LCJibmJfcHJpY2VfdW5pdHMiOjcyMjE1MDk4OCwiY2FwdHVyZV9oYXNoIjoiNDA3YTA4ZTc0NGFhYWFmOTVlMzBmMDA2ZGViNTZhNTliMjIwYTJiYjJmZTFmOGI5YjIxYjRmYzExODk4NmVjZCIsIm9ic2VydmVkX2F0IjoiMjAyNi0xMC0xOVQyMzo1NzowNi42MDBaIiwib3JpZ2luIjoiUkVDT1JERURfV0VCMyIsInNjaGVtYSI6IlF1b3RlQ29zdFN1bW1hcnkudjEiLCJzeW1ib2xzIjp7IkdPT0dMQiI6eyJhcHByb3ZlX2dhc19ibmJfdW5pdHMiOjQ1MzUxMTYxMTAwMDAsImZlZV9icHMiOjAsIm1lZGlhbl9pbXBhY3RfYnBzIjoxLCJxdW90ZV90dGxfc2Vjb25kcyI6MzAsInNhbXBsZXMiOjM4NSwic2xpcHBhZ2VfYnBzIjo0LCJzcHJlYWRfYnBzIjozLCJzd2FwX2dhc19ibmJfdW5pdHMiOjcxNTg3MzM2NjQ0MDAwfSwiTVNGVEIiOnsiYXBwcm92ZV9nYXNfYm5iX3VuaXRzIjo0NTU1MzU1NjMwMDAwLCJmZWVfYnBzIjowLCJtZWRpYW5faW1wYWN0X2JwcyI6MSwicXVvdGVfdHRsX3NlY29uZHMiOjMwLCJzYW1wbGVzIjozODQsInNsaXBwYWdlX2JwcyI6OCwic3ByZWFkX2JwcyI6MTcsInN3YXBfZ2FzX2JuYl91bml0cyI6NzA5MDMyMDE4NjAwMDB9LCJOVkRBQiI6eyJhcHByb3ZlX2dhc19ibmJfdW5pdHMiOjQ1MTcxNTgyNDAwMDAsImZlZV9icHMiOjAsIm1lZGlhbl9pbXBhY3RfYnBzIjoxLCJxdW90ZV90dGxfc2Vjb25kcyI6MzAsInNhbXBsZXMiOjM4NSwic2xpcHBhZ2VfYnBzIjo2LCJzcHJlYWRfYnBzIjo0LCJzd2FwX2dhc19ibmJfdW5pdHMiOjcxNjYwNDc1OTM2MDAwfSwiU0tIWUIiOnsiYXBwcm92ZV9nYXNfYm5iX3VuaXRzIjo0NTIyMjM3NzkwMDAwLCJmZWVfYnBzIjowLCJtZWRpYW5faW1wYWN0X2JwcyI6MSwicXVvdGVfdHRsX3NlY29uZHMiOjMwLCJzYW1wbGVzIjozODUsInNsaXBwYWdlX2JwcyI6OCwic3ByZWFkX2JwcyI6Miwic3dhcF9nYXNfYm5iX3VuaXRzIjo3MDY0NzYyNDQ2ODAwMH0sIlRTTEFCIjp7ImFwcHJvdmVfZ2FzX2JuYl91bml0cyI6NDUyNzAwNzI0MDAwMCwiZmVlX2JwcyI6MCwibWVkaWFuX2ltcGFjdF9icHMiOjEsInF1b3RlX3R0bF9zZWNvbmRzIjozMCwic2FtcGxlcyI6Mzg1LCJzbGlwcGFnZV9icHMiOjYsInNwcmVhZF9icHMiOjUsInN3YXBfZ2FzX2JuYl91bml0cyI6NzA3MTgyNDE2MDAwMDB9fX0sInJlZF9mbGFnX2F1dGhvcml0eSI6eyJlbmFibGVkIjpbIlJGMS1JVEVNLTQuMDIiLCJSRjItSVRFTS0xLjA1IiwiUkYyLUlURU0tMi4wNiJdLCJzZXRfc2hhMjU2IjoiMDI1OTMxMWIyYzE1ZWQ1MWYwZGY1MTQ5MGIzNmVjNGE0NTQ1YWY4ZmY1MjAyMjJmNWZhY2MxMzgxMjI2YWU1NSJ9LCJyZWRfZmxhZ19wb2xpY3kiOiJJREVBLTAzNS1CMSIsInJldmlld19zZXNzaW9ucyI6NSwicnVuX2hhbHRfcmVjb3ZlcnlfYnBzIjo1MDAsInMxIjp7ImV4ZWN1dGlvbiI6eyJjbG9zZV9idWZmZXJfc2Vjb25kcyI6OTAwLCJob3VycyI6IktJVF9PUEVOX1NUQVRFIiwibWF4X2F0dGVtcHRzX3Blcl9sZWdfc2Vzc2lvbiI6NSwib3Blbl9kZWxheV9zZWNvbmRzIjoxODAwfSwiaGFyZF9uYW1lX3dlaWdodCI6WzcsMjBdLCJsZXZlbHMiOnsiaGlnaCI6WzE5LDIwXSwibG93IjpbMywxMF0sIm1pZCI6WzMsNV19LCJsaW1pdGVyX21vZGUiOiJERVRFUk1JTklTVElDIiwibGxtX2V4cGlyeV9zZXNzaW9ucyI6MywibWF4X2xlZ3NfcGVyX3N5bWJvbF9zZXNzaW9uIjozLCJ0b3BfdXBfYmFuZCI6WzEsMjBdLCJ0cmVuZF9iYW5kX2JwcyI6MTAwLCJ0cmVuZF9kZWxheV9zZWNvbmRzIjo5MDAsInRyZW5kX3N0YXJ0X3N0YXRlIjoiVVAiLCJ0cmVuZF93aW5kb3dfc2Vzc2lvbnMiOjUsIndlaWdodF9jYXAiOlszLDEwXSwid2VpZ2h0cyI6eyJHT09HTEIiOlsxLDVdLCJNU0ZUQiI6WzEsNV0sIk5WREFCIjpbMSw1XSwiU0tIWUIiOlsxLDVdLCJUU0xBQiI6WzEsNV19fSwiczFfY2FwaXRhbF9iYXNpcyI6IkVYQ0xVREVfR0FTIiwiczFfcmVkdWN0aW9uX2Nvc3RfY2FwX2JwcyI6NTAsInM1X2VudHJ5X2Nvc3RfY2FwX2JwcyI6MjAwLCJzY2hlbWEiOiJTdHJhdGVneVByb2ZpbGUudjEiLCJzZXJpZXNfa2luZCI6IlRPS0VOIiwic2lnbmluZ19lbmQiOiIyMDI2LTEwLTI3VDE2OjAwOjAwWiIsInNsaXBwYWdlX2JwcyI6MjAsInN0YXRlbWVudF9hdXRob3JpdHkiOiJTSEFET1ciLCJzdWJtaXNzaW9uX21hcmdpbl9zZWNvbmRzIjozMCwidHJhZGVfYWZ0ZXIiOiIyMDI2LTEwLTI3VDA4OjAwOjAwWiIsInZhbHVlc19vcmlnaW4iOiJNRUFTVVJFRF9BTkRfREVDSURFRCJ9Cg=='
import base64
from datetime import datetime, timezone
import hashlib
import json
import re
import statistics
import time
import zlib

# Canonical larp/execution_live/untrusted_router.py at codex/system-testing-20261012 697ff3a. The host release
# predates it, so its exact bytes travel here and are loaded in memory after the hash check.
ROUTER_MODULE_SHA256 = '9934f5372f406ad9b9b62e85da93421128d68fdf2722af234f358d6140b0923a'
ROUTER_MODULE_Z = (
    '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'
    '7kw='
)
CLAIMS = ('LD02 operator packet. Not native-trace, signed-path or #92 evidence; the router draft stays '
          'REVIEW_REQUIRED and nothing is enabled.')
CONFIGS = {'runtime': '/etc/larp/runtime.json', 'release_manifest': '/etc/larp/release.json',
           'strategy_profile': '/etc/larp/strategy-profile.json'}
ALLOWANCE_CALL, APPROVE_CALL = '0xdd62ed3e', '0x095ea7b3'
RPC_METHODS = frozenset(('eth_chainId', 'eth_getBlockByNumber', 'eth_gasPrice', 'eth_call', 'eth_estimateGas',
                         'eth_getStorageAt'))
# LD03's reviewed policy (IDEA-070 LD03), exact file bytes; LD02b decodes this run's fresh quotes under it.
POLICY_SHA256 = '05759e90b87511210a6dce953a9cd2f1e2c8a36a219988905a10b66c127957c5'
POLICY_JSON = '{\n  "chain_id": 56,\n  "deviation": "DEV-23",\n  "diamond_storage_base": "0x5e12654f390e4153c4f63b3dfcc122cf7876a5cdfb496dccf7284c10517a35c5",\n  "facet": "0xa9fa1b56f4d7bd25375c2d40b4c8e36a9509e603",\n  "facet_codehash": "0x5ae2caa18a9d1d2dc528e6a1e9edf284883c023a617cc269b96620e4712d8ba0",\n  "facet_slot": "0x7ddc1c45a5ae31800e181de98e8cb97525e9b89f99e5829d49f25a8ca4bac1d7",\n  "fixed_words": {\n    "1": "0x0000000000000000000000000000000000000000000000000000000000000000",\n    "2": "0x0000000000000000000000003d90f66b534dd8482b181e24655a9e8265316be9",\n    "7": "0x000000000000000000000000d2a27f8fdbaaec431d59046a8bce4e5db665a271",\n    "9": "0x0000000000000000000000000000000000000000000000000000000000000140"\n  },\n  "inner_selector": "0x47ee97ff",\n  "review": {\n    "review_ref": "IDEA-070 LD03 (2026-10-20)",\n    "reviewed_by": "Keegan (Weixuan Keegan Gan)"\n  },\n  "router": "0xb44446b0c8e56988c34f7ff73ae904982b5fdda5",\n  "router_codehash": "0xb6f35276cf3608595df59a3cfa5fb06a3309e64e387b0ea4f60875fdc4c696a0",\n  "schema": "UntrustedRouterPolicy.v1",\n  "selector": "0xad43f73d"\n}\n'
# Binance-Peg BSC-USD (BEP20Token): _balances at slot 1 and _allowances at slot 2, proven on chain before use (G4).
USDT_BALANCE_SLOT, USDT_ALLOWANCE_SLOT = 1, 2
OVERRIDE_ALLOWANCE = 2**255
SIGNER_TIMINGS = ('queue_ms', 'sign_ms', 'broadcast_ms', 'receipt_ms', 'finality_ms')


def fingerprint(value):
    return hashlib.sha256(str(value).encode()).hexdigest()[:16]


def iso(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def epoch_s(stamp):
    return datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()


OWN_CODES = frozenset(('CALLDATA_LAYOUT', 'CALLDATA_SELECTOR', 'NO_BALANCE_PROVIDERS', 'ROUTER_MODULE_HASH',
                       'RPC_CALL_REFUSED', 'RPC_METHOD_REFUSED', 'RPC_REFUSED', 'SANITIZER_FORBIDDEN_VALUE',
                       'SANITIZER_URL', 'POLICY_HASH'))


def refusal(error):
    """The only output when the packet is refused. It bypasses the final scan, so it carries the exception type and
    nothing else, except one of this script's own codes from the explicit allowlist (PR205 review P2)."""
    text = str(error)
    return dict(error='LD02_PACKET_REFUSED', signing_enabled=False,
                reason=type(error).__name__ + (':' + text if text in OWN_CODES else ''))


def code(error):
    """An error's type, plus a short code or fixed phrase, for fields inside the packet; the final scan still applies."""
    text = str(error)
    return type(error).__name__ + (':' + text if re.fullmatch(r'[A-Za-z0-9_ ,.-]{3,100}', text) else '')


def load_router_module():
    import types
    raw = zlib.decompress(base64.b64decode(''.join(ROUTER_MODULE_Z)))
    if hashlib.sha256(raw).hexdigest() != ROUTER_MODULE_SHA256:
        raise ValueError('ROUTER_MODULE_HASH')
    module = types.ModuleType('ld02_untrusted_router')
    exec(compile(raw, 'untrusted_router.py@697ff3a', 'exec'), module.__dict__)
    return module


class MemoryArtifacts:
    """`Artifacts.put` without a disk write: the packet keeps hashes, never the stored bytes."""

    def __init__(self):
        self.records = []

    def put(self, observation):
        raw = json.dumps(observation, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        self.records.append(json.loads(raw))  # a copy: the client later adds artifact_sha256 to its own dict
        return hashlib.sha256(raw).hexdigest()


class TimedOpener:
    """Wraps the production opener and logs (source, method, ms to response headers)."""

    def __init__(self, inner, log, source_id):
        self.inner, self.log, self.source_id = inner, log, source_id

    def open(self, request, timeout=None):
        method = json.loads(request.data).get('method')
        start = time.monotonic()
        try:
            return self.inner.open(request, timeout=timeout)
        finally:
            self.log.append((self.source_id, method, round((time.monotonic() - start) * 1000)))


def word_hex(value):
    return format(value, '064x')


def mapping_slot(key, slot):
    """Solidity mapping slot keccak256(pad(key) || pad(slot)); `key` is an address or a 0x word."""
    from eth_utils import keccak
    position = word_hex(slot if type(slot) is int else int(slot, 16))
    return '0x' + keccak(bytes.fromhex(str(key)[2:].rjust(64, '0') + position)).hex()


def allowed_call(method, params, scope):
    """G5: the only shapes this script may send. `scope` = {wallet, router, usdt, tokens, calldata}."""
    def override_ok(value):
        if scope is None or type(value) is not dict:
            return False
        slot = mapping_slot(scope['router'], mapping_slot(scope['wallet'], USDT_ALLOWANCE_SLOT))
        return value == {scope['usdt']: {'stateDiff': {slot: '0x' + word_hex(OVERRIDE_ALLOWANCE)}}}
    if method in ('eth_chainId', 'eth_getBlockByNumber', 'eth_gasPrice'):
        return True
    tx = params[0] if params and type(params[0]) is dict else {}
    data = str(tx.get('data', ''))
    if method == 'eth_call':
        return data[:10] == ALLOWANCE_CALL and (len(params) == 2 or (len(params) == 3 and override_ok(params[2])))
    if method == 'eth_getStorageAt':
        return scope is not None and params[0] == scope['usdt'] and len(params) == 3
    if method == 'eth_estimateGas' and scope is not None:
        if set(tx) - {'from', 'to', 'data', 'value'} or tx.get('from') != scope['wallet'] or tx.get('value', '0x0') != '0x0':
            return False
        if len(params) == 3 and not override_ok(params[2]) or len(params) not in (2, 3):
            return False
        approve = (tx.get('to') in scope['tokens'] and data[:10] == APPROVE_CALL and len(data) == 138
                   and data[10:74] == scope['router'][2:].rjust(64, '0'))
        return approve or (tx.get('to') == scope['router'] and data in scope['calldata'])
    return False


ERROR_STRING = '0x08c379a0'


class RpcRefused(ValueError):
    """A JSON-RPC error reply. str() stays the plain code; `detail()` is a filtered summary (LD02b-F1)."""

    def __init__(self, error):
        super().__init__('RPC_REFUSED')
        self.error = error

    def detail(self, forbidden=()):
        e = self.error
        out = dict(rpc_code=e.get('code') if type(e.get('code')) is int else None)
        message = str(e.get('message', ''))
        out['message'] = plain(message, forbidden)
        data = e.get('data')
        if type(data) is str and re.fullmatch(r'0x[0-9a-fA-F]*', data) and len(data) >= 10:
            out['revert_selector'] = data[:10].lower()
            if data[:10].lower() == ERROR_STRING:
                out['revert_text'] = revert_text(data, forbidden)
        return out


def revert_text(data, forbidden=()):
    """The string of an ABI `Error(string)` revert, through `plain()`; 'FILTERED' if it does not decode."""
    try:
        body = bytes.fromhex(data[10:])
        offset = int.from_bytes(body[:32], 'big')
        length = int.from_bytes(body[offset:offset + 32], 'big')
        text = body[offset + 32:offset + 32 + length].decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return 'FILTERED'
    return plain(text, forbidden)


def plain(text, forbidden=()):
    """Printable ASCII (others shown as '?'), at most 160 characters with the full length noted; a URL is
    'FILTERED'. The final scan still refuses secrets and the wallet."""
    if '://' in text:
        return 'FILTERED'
    # Scan the complete value before truncation or ASCII replacement can hide
    # part of a known credential/address from the final serialized-packet scan.
    sanitize(text, forbidden)
    shown = ''.join(c if ' ' <= c <= '~' else '?' for c in text)
    return shown if len(shown) <= 160 else shown[:160] + f'...[{len(shown)} chars]'


def rpc(url, source_id, method, params, log, scope=None):
    """One read-only JSON-RPC call outside the production client (allowance, gas, storage, finality)."""
    from urllib.request import Request, build_opener
    from larp.marketdata.web3 import NoRedirect
    if method not in RPC_METHODS or not url.startswith('https://'):
        raise ValueError('RPC_METHOD_REFUSED')
    if not allowed_call(method, params, scope):
        raise ValueError('RPC_CALL_REFUSED')
    body = json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode()
    start = time.monotonic()
    with build_opener(NoRedirect()).open(Request(url, data=body, headers={'Content-Type': 'application/json'}),
                                         timeout=20) as response:
        reply = json.loads(response.read(2 * 1024 * 1024))
    log.append((source_id, method, round((time.monotonic() - start) * 1000)))
    if type(reply) is dict and type(reply.get('error')) is dict:
        raise RpcRefused(reply['error'])
    if type(reply) is not dict or 'result' not in reply:
        raise ValueError('RPC_REFUSED')
    return reply['result']


def timing_summary(log):
    groups = {}
    for source, method, ms in log:
        groups.setdefault(f'{source}:{method}', []).append(ms)
    return {k: dict(n=len(v), min=min(v), median=statistics.median(v), max=max(v)) for k, v in sorted(groups.items())}


def word(body, index):
    return int.from_bytes(body[32 * index:32 * index + 32], 'big')


def inner_deadline(data, m):
    """The route's inner deadline, read with the canonical layout constants (IDEA-070 B02-U)."""
    if type(data) is not str or not data.startswith(m.SWAP_SELECTOR):
        raise ValueError('CALLDATA_SELECTOR')
    body = bytes.fromhex(data[10:])
    if len(body) < 32 * m.HEAD_WORDS:
        raise ValueError('CALLDATA_LAYOUT')
    start, length = 32 * m.HEAD_WORDS, word(body, m.BLOB_LENGTH)
    inner = body[start:start + length]
    if length < 4 + 32 * m.INNER_WORDS or '0x' + inner[:4].hex() != m.INNER_SELECTOR:
        raise ValueError('CALLDATA_LAYOUT')
    return word(inner[4:], m.INNER_DEADLINE)


def quote_row(symbol, side, pay_units, amount, decimals, record, m, tokens, usdt):
    """A request-bound summary of one quote: binding booleans, timings and the route deadline, no calldata."""
    data = record['response']['data']
    q = data[0] if isinstance(data, list) and len(data) == 1 else data
    rr, tx = q.get('routerResult') or {}, q.get('tx') or {}
    pay, receive = (usdt, tokens[symbol]) if side == 'BUY' else (tokens[symbol], usdt)
    pay_decimals, receive_decimals = (18, decimals) if side == 'BUY' else (decimals, 18)
    bound = (str(rr.get('fromToken', {}).get('tokenContractAddress', '')).lower() == pay
             and str(rr.get('toToken', {}).get('tokenContractAddress', '')).lower() == receive
             and int(rr['fromToken']['decimal']) == pay_decimals and int(rr['toToken']['decimal']) == receive_decimals
             and int(rr['fromTokenAmount']) == amount)
    received, minimum = int(rr['toTokenAmount']), int(tx['minReceiveAmount'])
    row = dict(symbol=symbol, side=side, pay_units=pay_units, status='OK', request_bound=bound,
               router_pinned=str(tx.get('to', '')).lower() == m.ROUTER, native_value_zero=int(tx.get('value', 0)) == 0,
               selector_pinned=str(tx.get('data', ''))[:10] == m.SWAP_SELECTOR, vendor=rr.get('vendorName'),
               elapsed_ms=record.get('elapsed_ms'), quoted_gas=int(tx['gas']) if tx.get('gas') else None,
               receive_units=received, minimum_receive=minimum,
               minimum_below_quote_bps=(received - minimum) * 10000 // received if received else None,
               impact_percent=rr.get('priceImpactPercent'),
               calldata=fingerprint(tx.get('data')), artifact=record['artifact_sha256'][:16])
    try:
        row['deadline_after_request_s'] = round(inner_deadline(tx['data'], m) - epoch_s(record['requested_at']), 1)
    except (ValueError, KeyError, TypeError) as error:
        row['deadline_after_request_s'], row['deadline_error'] = None, code(error)
    return row


def memory_quotes(records):
    """`untrusted_router._quotes` over this run's in-memory quote records (same fields it reads from files)."""
    for value in records:
        if value.get('endpoint') != 'aggregator/quote-and-swap' or value.get('outcome') != 'ok':
            continue
        data = value['response']['data']
        data = data[0] if isinstance(data, list) and len(data) == 1 else data
        tx = data.get('tx') if isinstance(data, dict) else None
        if type(tx) is dict and str(tx.get('data', '')).startswith('0x'):
            raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
            yield hashlib.sha256(raw).hexdigest(), value['params'], tx


def policy_check(module, draft):
    """G1/G2: the reviewed policy, hash-pinned, against this run's live draft and fresh calldata."""
    raw = POLICY_JSON.encode()
    if hashlib.sha256(raw).hexdigest() != POLICY_SHA256:
        raise ValueError('POLICY_HASH')
    policy = json.loads(raw)
    unreviewed = {k: v for k, v in policy.items() if k != 'review'}
    try:
        report = module.check(module.UntrustedRouterDecoder(policy, policy_sha256=POLICY_SHA256), None)
    except Exception as error:
        return dict(policy_sha256=POLICY_SHA256, status='REFUSED', error=code(error))
    rows = [dict(artifact=r['artifact_sha256'][:16], status=r['status'], matches_quote=r.get('matches_quote'),
                 tampered_refused=r.get('tampered_refused'),
                 **({'refused': r['refused']} if re.fullmatch(r'[A-Za-z ,.-]{3,100}', str(r.get('refused', ''))) else {}))
            for r in report['rows']]
    return dict(policy_sha256=POLICY_SHA256, status=report['status'], quotes=report['quotes'], rows=rows,
                matches_live_draft=None if draft is None else unreviewed == {k: v for k, v in draft.items() if k != 'review'},
                signing_enabled=False)


def estimate(provider, params, log, scope):
    """(gas, None) or (None, reason): a code, or the RpcRefused detail. A simulation only, never a transaction."""
    try:
        return int(rpc(provider['url'], provider['source_id'], 'eth_estimateGas', params, log, scope), 16), None
    except RpcRefused as refusal:
        return None, dict(code='RPC_REFUSED', **refusal.detail((scope or {}).get('forbidden', ())))
    except ValueError as error:
        return None, str(error) if str(error) in OWN_CODES else 'ValueError'
    except Exception as error:
        return None, type(error).__name__


def gas_estimates(provider, scope, observation, calldata, sizes, log, tokens):
    """G3/G4: approve gas per token, and BUY swap gas under a proven USDT allowance override, at one block."""
    from larp.execution import USDT
    url, sid = provider['url'], provider['source_id']
    block = rpc(url, sid, 'eth_getBlockByNumber', ['latest', False], log, scope)['number']
    wallet, router = scope['wallet'], scope['router']
    out = dict(block=int(block, 16), served_by=sid, approve={}, swap_buy_minimum={},
               note='eth_estimateGas simulations at one block; not measured fills. LD09 inputs only.')
    for name, token in (('USDT', USDT), *tokens.items()):
        data = APPROVE_CALL + router[2:].rjust(64, '0') + word_hex(sizes.get(name, 1))
        gas, reason = estimate(provider, [dict({'from': wallet, 'to': token, 'data': data, 'value': '0x0'}), block],
                               log, scope)
        out['approve'][name] = gas if gas is not None else dict(error=reason)  # reason may be a detail dict
    proof = dict(balance_slot_matches=False, override_effective=False)
    try:
        balance = int(rpc(url, sid, 'eth_getStorageAt', [USDT, mapping_slot(wallet, USDT_BALANCE_SLOT), block],
                          log, scope), 16)
        proof['balance_slot_matches'] = balance == observation['tokens']['USDT']['units']
        slot = mapping_slot(router, mapping_slot(wallet, USDT_ALLOWANCE_SLOT))
        override = {USDT: {'stateDiff': {slot: '0x' + word_hex(OVERRIDE_ALLOWANCE)}}}
        seen = rpc(url, sid, 'eth_call', [dict(to=USDT, data=ALLOWANCE_CALL + wallet[2:].rjust(64, '0')
                                               + router[2:].rjust(64, '0')), block, override], log, scope)
        proof['override_effective'] = int(seen, 16) == OVERRIDE_ALLOWANCE
    except Exception as error:
        proof['error'] = code(error) if isinstance(error, ValueError) else type(error).__name__
    out['allowance_override_proof'] = proof
    if not (proof['balance_slot_matches'] and proof['override_effective']):
        out['swap_buy_minimum'] = dict(status='NOT_ESTIMATED', reason='allowance override not proven')
        return out
    for symbol, data in sorted(calldata.items()):
        gas, reason = estimate(provider, [{'from': wallet, 'to': router, 'data': data, 'value': '0x0'}, block, override],
                               log, scope)
        out['swap_buy_minimum'][symbol] = gas if gas is not None else dict(error=reason)
    return out


def finality(providers, log):
    rows = []
    for p in providers:
        try:
            latest = rpc(p['url'], p['source_id'], 'eth_getBlockByNumber', ['latest', False], log)
            final = rpc(p['url'], p['source_id'], 'eth_getBlockByNumber', ['finalized', False], log)
            rows.append(dict(source_id=p['source_id'], latest=int(latest['number'], 16), finalized=int(final['number'], 16),
                             lag_blocks=int(latest['number'], 16) - int(final['number'], 16),
                             lag_seconds=int(latest['timestamp'], 16) - int(final['timestamp'], 16)))
        except Exception as error:
            rows.append(dict(source_id=p['source_id'], status='REFUSED', error=code(error)))
    return rows


def sanitize(text, forbidden):
    """Refuse the packet if it carries a URL, a secret, the wallet or a database endpoint."""
    if '://' in text:
        raise ValueError('SANITIZER_URL')
    low = text.lower()
    for value in forbidden:
        if value and len(value) >= 6 and value.lower() in low:
            raise ValueError('SANITIZER_FORBIDDEN_VALUE')
    return text


def forbidden_values(config, secrets, providers):
    from urllib.parse import urlsplit
    wallet = str(config.get('wallet_address', '')).lower()
    values = [wallet, wallet[2:], config.get('database_host')]
    for p in providers:
        values += [p.get('url'), urlsplit(p.get('url', '')).hostname]
    return values + [v for v in secrets.values() if isinstance(v, str)]


def read_configs():
    raw = {}
    for name, path in CONFIGS.items():
        with open(path, 'rb') as stream:
            raw[name] = stream.read()
    return raw


def database(config):
    from contextlib import contextmanager
    from larp.runtime.database import IamPostgresStore, rds_client

    class RO(IamPostgresStore):
        @contextmanager
        def transaction(self):
            with super().transaction() as db:
                db.execute('SET TRANSACTION READ ONLY'); yield db

    with RO(config, rds_client(config['region'])).transaction() as db:
        run = db.execute('SELECT wallet_id,version,epoch,quarantined,projection FROM runs WHERE run_id=%s',
                         (config['run_id'],)).fetchone()
        reservations = db.execute('SELECT asset,count(*),sum(units) FROM reservations WHERE run_id=%s GROUP BY asset',
                                  (config['run_id'],)).fetchall()
        commands = db.execute('SELECT status,count(*) FROM commands WHERE run_id=%s GROUP BY status',
                              (config['run_id'],)).fetchall()
        rounds = db.execute('SELECT status,count(*) FROM rounds WHERE run_id=%s GROUP BY status',
                            (config['run_id'],)).fetchall()
    return run, reservations, commands, rounds


def collect():
    from larp.contracts import Document
    from larp.execution import USDT
    from larp.execution_live.balances import BalanceProviders, DecimalsCache
    from larp.execution_live.chain import Rpc
    from larp.marketdata.port import TOKENS, MarketPort
    from larp.marketdata.web3 import NoRedirect, Web3Client
    from larp.risk.reconcile import compare_balances
    from larp.runtime.credentials import runtime_secrets
    from urllib.request import build_opener
    import socket

    module = load_router_module()
    before = read_configs()
    config, profile = json.loads(before['runtime']), json.loads(before['strategy_profile'])
    selected_raw = base64.b64decode(SELECTED_PROFILE_B64)
    profile = json.loads(selected_raw)
    driver = config['driver']
    providers = list(driver.get('balance_rpc_providers') or [])
    if not providers:
        raise ValueError('NO_BALANCE_PROVIDERS')
    wallet = config['wallet_address'].lower()
    secrets = runtime_secrets(config)
    forbidden = [v for v in forbidden_values(config, secrets, providers) if not isinstance(v, str) or v.lower() not in (wallet, wallet[2:])]
    log, quote_log = [], []
    packet = dict(schema='LD02ExecutionPacket.v1', generated_utc=iso(time.time_ns() // 1000000), claims=CLAIMS,
                  signing_enabled=False, router_module_sha256=ROUTER_MODULE_SHA256)

    run, reservations, commands, rounds = database(config)
    projection = Document(bytes(run[4])).read()
    portfolio, registered = projection.get('portfolio') or {}, projection.get('registered_version') or {}
    hashes = {k: hashlib.sha256(v).hexdigest() for k, v in before.items()}
    packet['identity'] = dict(
        host=socket.gethostname(), run_id=config['run_id'], build_id=config.get('build_id'), mode=config.get('mode'),
        execution=driver.get('execution'), database_name=config.get('database_name'),
        config_sha256=hashes, wallet_fingerprint=fingerprint(wallet),
        wallet_consistent=wallet == str(run[0]).lower() == str(portfolio.get('wallet_id', '')).lower(),
        registered_build_matches=registered.get('build_id') == config.get('build_id'),
        registered_manifest_matches=registered.get('manifest_sha256') == hashes['release_manifest'],
        run=dict(version=run[1], epoch=run[2], quarantined=run[3]))
    packet['in_flight'] = dict(
        reservations={a: dict(count=n, units=int(u)) for a, n, u in reservations},
        commands=dict(commands), rounds=dict(rounds),
        execution_pending=sorted(r for r, rec in (projection.get('round_records') or {}).items()
                                 if rec.get('execution_pending')),
        settled_block=projection.get('settled_block'))
    packet['finality_start'] = finality(providers, log)

    # Holdings: the production ordered-provider reader and reconciliation against the current ledger.
    reader = BalanceProviders(
        [Rpc(p['url'], artifacts=MemoryArtifacts(), source_id=p['source_id'],
             opener=TimedOpener(build_opener(NoRedirect()), log, p['source_id'])) for p in providers],
        wallet=wallet, decimals=DecimalsCache(), min_block=lambda: projection.get('settled_block'))
    observed_ms = time.time_ns() // 1000000
    observation = reader(observed_ms)
    plain = {k: v for k, v in observation.items() if k != 'source_id'}
    check = compare_balances(portfolio, plain, settled_block=projection.get('settled_block'))
    packet['holdings'] = dict(
        observed_utc=iso(observed_ms), served_by=observation['source_id'], block=observation['block_number'],
        block_hash=observation['block_hash'], observation_sha256=Document.from_dict(observation).digest('ChainBalances.v1'),
        status=check['status'], assets={a: dict(cls=r['class'], ledger=r['ledger_units'], chain=r['chain_units'])
                                        for a, r in check['assets'].items()},
        native_wei=observation['native_wei'], latest_nonce=observation['latest_nonce'],
        pending_nonce=observation['pending_nonce'], note='fresh read in this run, not a #92 citation')

    # Request-bound quotes at the profile's planned sizes, with its slippage, through the runtime's own port.
    web3 = MemoryArtifacts()
    port = MarketPort(Web3Client(secrets['BINANCE_API_KEY'], secrets['BINANCE_SECRET_KEY'], artifacts=web3), wallet,
                      quote_limits=profile)
    minimum, cap = profile.get('minimum_trade_units'), profile.get('per_trade_cap_units')
    quotes, calldata = [], {}
    for symbol in TOKENS:
        decimals = observation['tokens'][symbol]['decimals']
        sell_units = None
        steps = [('BUY', minimum), ('BUY', cap), ('SELL', None)]
        for side, units in steps:
            if side == 'SELL' and units is None:
                units = sell_units
            if type(units) is not int or units <= 0:
                quotes.append(dict(symbol=symbol, side=side, status='NOT_REQUESTED', reason='SIZE_UNAVAILABLE'))
                continue
            amount = units * 10**12 if side == 'BUY' else units
            try:
                record = port.quote(symbol, side, amount, decimals)
                row = quote_row(symbol, side, units, amount, decimals, record, module, TOKENS, USDT)
                if side == 'SELL' and len(steps) == 3:
                    steps.extend(('SELL', c) for c in sorted(set(exit_children(
                        units, row['receive_units'], cap * 10**12, 2))) if c != units)
                if side == 'BUY':
                    sell_units = max(sell_units or 0, row['receive_units'])
                if side == 'BUY' and units == minimum:
                    sell_units = row['receive_units']
                    data = record['response']['data']
                    calldata[symbol] = (data[0] if isinstance(data, list) else data)['tx']['data']
            except Exception as error:
                row = dict(symbol=symbol, side=side, pay_units=units, status='REFUSED', error=code(error))
            quotes.append(row)
    packet['quotes'] = dict(sizes=dict(minimum_trade_units=minimum, per_trade_cap_units=cap,
                                       slippage_bps=profile.get('slippage_bps')), rows=quotes)

    # Router/facet/code draft from live state and this run's quotes; it stays REVIEW_REQUIRED.
    module._quotes = lambda _directory: memory_quotes(web3.records)
    try:
        draft, block, count = module.observe(providers[0]['url'], None)
        text = json.dumps(draft, indent=2, sort_keys=True) + '\n'
        allowances = {}
        owner, spender = wallet[2:].rjust(64, '0'), module.ROUTER[2:].rjust(64, '0')
        for name, token in (('USDT', USDT), *TOKENS.items()):
            value = rpc(providers[0]['url'], providers[0]['source_id'], 'eth_call',
                        [dict(to=token, data=ALLOWANCE_CALL + owner + spender), block], log)
            allowances[name] = int(value, 16)
        packet['router'] = dict(status='DRAFT_REVIEW_REQUIRED', block=int(block, 16), quotes_used=count,
                                draft_sha256=hashlib.sha256(text.encode()).hexdigest(), draft=draft,
                                allowances_to_router=allowances, served_by=providers[0]['source_id'])
    except Exception as error:
        packet['router'] = dict(status='REFUSED', error=code(error))
        draft = None

    packet['policy_check'] = policy_check(module, draft)
    scope = dict(wallet=wallet, router=module.ROUTER, usdt=USDT, tokens={USDT, *TOKENS.values()},
                 calldata=set(calldata.values()), forbidden=forbidden)
    sizes = {'USDT': minimum * 10**12 if type(minimum) is int else 1}
    sizes.update({r['symbol']: r['pay_units'] for r in quotes if r.get('side') == 'SELL' and r.get('status') == 'OK'})
    packet['gas_estimates'] = gas_estimates(providers[0], scope, observation, calldata, sizes, log, TOKENS)

    # Funding input for Isaac (LD07: initial gas only). Not a decision: LD09's measured gas is still missing.
    gas_price = int(rpc(providers[0]['url'], providers[0]['source_id'], 'eth_gasPrice', [], log), 16)
    swap_gas = [r['quoted_gas'] for r in quotes if r.get('status') == 'OK' and r.get('quoted_gas')]
    median_gas = int(statistics.median(swap_gas)) if swap_gas else None
    bnb_value = observation['native_wei'] * portfolio['bnb_price_units'] // 10**18 if portfolio.get('bnb_price_units') else None
    reserve = profile.get('exit_gas_reserve_units')
    packet['funding_input'] = dict(
        native_wei=observation['native_wei'], bnb_value_units=bnb_value, gas_price_wei=gas_price,
        median_quoted_swap_gas=median_gas,
        indicative_swaps_affordable=observation['native_wei'] // (median_gas * gas_price) if median_gas and gas_price else None,
        exit_gas_reserve_wei=reserve,  # the planner compares it with ledger bnb_units (wei), not USDT value
        versus_exit_reserve=None if type(reserve) is not int else
        ('BELOW_EXIT_RESERVE' if observation['native_wei'] < reserve else 'AT_OR_ABOVE_EXIT_RESERVE'),
        reserve_multiple=round(observation['native_wei'] / reserve, 2) if type(reserve) is int and reserve > 0 else None,
        approve_gas='UNMEASURED', ld09_measured_gas='UNMEASURED',
        note='Input for Isaac against LD07 (initial gas only); seeding needs LD09 measured gas x planned trades x margin.')

    configured = []
    for path in sorted(__import__('glob').glob('/etc/larp/*.json')):
        try:
            with open(path, 'rb') as stream:
                doc = json.loads(stream.read())
        except ValueError:
            continue
        for key in ('execution_rpc_url', 'rpc_url', 'execution_rpc_providers', 'rpc_providers'):
            if isinstance(doc, dict) and key in doc:
                configured.append(dict(file=path.rsplit('/', 1)[-1], key=key))
    packet['execution_rpc'] = dict(
        configured_on_primary=configured,
        candidates=[dict(source_id=p['source_id'], url_fingerprint=fingerprint(p['url']),
                         approved_for='development balance reads') for p in providers],
        status='AWAITING_KEEGAN_CONFIRMATION')
    packet['signer_timings'] = dict(status='UNMEASURED', fields=list(SIGNER_TIMINGS),
                                    reason='no signer installed; the signer host was not queried')
    packet['finality_end'] = finality(providers, log)
    packet['timings'] = dict(rpc_ms=timing_summary(log), quote_ms=timing_summary(
        [('BINANCE_WEB3', 'quote-and-swap', r['elapsed_ms']) for r in quotes if r.get('elapsed_ms') is not None]))
    after = read_configs()
    packet['configs_unchanged'] = after == before
    packet['selected_profile_sha256'] = hashlib.sha256(selected_raw).hexdigest()
    packet['portfolio_source_sha256'] = Document.from_dict(portfolio).digest('PortfolioState.v1')
    caps_portfolio = {k: portfolio[k] for k in ('schema', 'wallet_id', 'run_id', 'mode', 'cash_units',
                                               'bnb_units', 'bnb_decimals', 'positions', 'reservations')}
    packet['private_caps_inputs'] = dict(wallet=wallet, portfolio=caps_portfolio,
        token_decimals={s: observation['tokens'][s]['decimals'] for s in TOKENS},
        quote_artifacts=web3.records)
    # Private review needs the public wallet address. Continue refusing secrets,
    # provider URLs and database endpoints; omit only public token image metadata.
    for record in packet['private_caps_inputs']['quote_artifacts']:
        record['original_record_sha256'] = hashlib.sha256(
            json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        record.pop('response_body_base64', None)  # exact upstream response_sha256 is retained
        response_data = record.get('response', {}).get('data')
        rows = response_data if isinstance(response_data, list) else [response_data]
        projected = []
        for row in rows:
            if isinstance(row, dict):
                rr, tx = row.get('routerResult', {}), row.get('tx', {})
                projected.append(dict(executionMode=row.get('executionMode'), rfq=row.get('rfq'),
                    routerResult=dict(fromToken={k: v for k, v in rr.get('fromToken', {}).items()
                                                 if k in ('tokenContractAddress', 'decimal')},
                                      toToken={k: v for k, v in rr.get('toToken', {}).items()
                                               if k in ('tokenContractAddress', 'decimal')},
                                      fromTokenAmount=rr.get('fromTokenAmount'),
                                      toTokenAmount=rr.get('toTokenAmount')),
                    tx={k: v for k, v in tx.items() if k in ('to', 'from', 'chainId', 'value', 'gas',
                                                           'gasPrice', 'minReceiveAmount')},
                    calldata_sha256=hashlib.sha256(str(tx.get('data', '')).encode()).hexdigest()))
        if isinstance(record.get('response'), dict):
            record['response'] = dict(code=record['response'].get('code'),
                                      data=projected if isinstance(response_data, list) else projected[0])
    return packet, forbidden


def main():
    packet, forbidden = collect()
    text = sanitize(json.dumps(packet, sort_keys=True, separators=(',', ':')), forbidden)
    print(base64.b64encode(zlib.compress(text.encode(), 9)).decode())
    print(json.dumps(dict(packet_sha256=hashlib.sha256(text.encode()).hexdigest())))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Neither config content nor provider/database text is emitted; only this script's own codes.
        print(json.dumps(refusal(error)))
        raise SystemExit(2)
PY
