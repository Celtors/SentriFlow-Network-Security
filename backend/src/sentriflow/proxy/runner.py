from mitmproxy.options import Options
from mitmproxy.tools.dump import DumpMaster

from sentriflow.proxy.addon import GuardianAddon
from sentriflow.runtime import Runtime


def create_master(runtime: Runtime) -> DumpMaster:
    options = Options(
        listen_host="127.0.0.1",
        listen_port=runtime.config.proxy_port,
        confdir=str((runtime.config.data_dir / "ca").resolve()),
        rawtcp=False,
        http3=False,
    )
    master = DumpMaster(options, with_dumper=False, with_termlog=False)
    master.options.update(connection_strategy="lazy", body_size_limit="8m")
    master.addons.add(GuardianAddon(runtime))
    return master
