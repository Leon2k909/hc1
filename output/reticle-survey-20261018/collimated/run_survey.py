import sys, subprocess, json, os
S = os.path.dirname(os.path.abspath(__file__))
CLI = r'D:\SteamLibrary\steamapps\common\sbox\bin\managed\sbox-cli.exe'
BS = chr(92)


def run(guns, out, lifts='0f', tag='run'):
    src = open(os.path.join(S, 'survey.cs.txt')).read()
    os.makedirs(os.path.join(S, 'cs'), exist_ok=True)
    g = ','.join('("%s","%s")' % x for x in guns)
    src = src.replace('__GUNS__', g).replace('__OUT__', out.replace('/', BS)).replace('__LIFTS__', lifts)
    path = os.path.join(S, 'cs', 'survey3-%s.cs' % tag)
    open(path, 'w').write(src)
    r = subprocess.run([CLI, '--request-timeout', '900', '--call', 'run_csharp', json.dumps({'path': path.replace(BS, '/')})],
                       capture_output=True, text=True, timeout=1000, cwd=r'C:\sbox-projects\hc1\forked-shooter-main')
    print(r.stdout[-2000:], r.stderr[-2000:])


GUNS = dict([("m4a1", "weapons/m4a1"), ("kastov74u", "weapons/kastov74u"), ("kastov762", "weapons/kastov"),
             ("vityaz", "weapons/vityaz"), ("rpk", "weapons/rpk"), ("bizon", "weapons/bizon"), ("ak105", "weapons/ak105"),
             ("vepr12", "weapons/vepr12"), ("m16", "weapons/m16"), ("p90", "weapons/p90"), ("mp7", "weapons/mp7"),
             ("aug", "weapons/aug"), ("uzi", "weapons/uzi"), ("fal", "weapons/fal"), ("famas", "weapons/famas"),
             ("mcx", "weapons/mcx"), ("l85a2", "weapons/l85a2"), ("hk416", "weapons/hk416"), ("ak12", "weapons/ak12"),
             ("ak15", "weapons/ak15"), ("ak74m", "weapons/ak74m"), ("spear", "weapons/spear"), ("rpk16", "weapons/rpk16")])

if __name__ == '__main__':
    names = sys.argv[3].split(',')
    run([(n, GUNS[n]) for n in names], sys.argv[1], sys.argv[2], sys.argv[4] if len(sys.argv) > 4 else 'run')
