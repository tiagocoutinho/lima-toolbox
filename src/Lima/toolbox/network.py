import asyncio

import aiodns
import netifaces


def get_ipv4_addresses():
    for interface in netifaces.interfaces():
        for addr in netifaces.ifaddresses(interface).get(netifaces.AF_INET, []):
            yield addr['addr']


def get_subnet_addresses():
    domains = (addr.rsplit('.', 1)[0] for addr in get_ipv4_addresses()
               if not addr.startswith('127'))
    addresses = set()
    for i in range(256):
        for domain in domains:
            addresses.add(f"{domain}.{i}")
    for addr in get_ipv4_addresses():
        if addr.startswith('127'):
            addresses.add(addr)
        else:
            # assuming 255.255.255.0 netmask
            domain = addr.rsplit('.', 1)[0]
            for i in range(256):
                addresses.add(f"{domain}.{i}")
    return addresses


async def get_host_by_addr(addr):
    return await aiodns.DNSResolver().gethostbyaddr(addr)


async def test_connection(host, port):
    try:
        r, w = await asyncio.open_connection(host, port)
        w.close()
        return host, True
    except OSError:
        return host, False


async def get_hosts(port, timeout=None):
    tasks = [asyncio.create_task(test_connection(addr, port))
             for addr in get_subnet_addresses()]
    for task in asyncio.as_completed(tasks, timeout=timeout):
        host, is_open = await task
        if is_open:
            yield host


async def main(port, timeout=None):
    async for host in get_hosts(port, timeout=timeout):
        print(host)


if __name__ == "__main__":
    asyncio.run(main(8000))
