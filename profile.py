#!/usr/bin/env python

import os

import geni.portal as portal
import geni.rspec.pg as rspec
import geni.rspec.igext as IG
import geni.rspec.emulab.pnext as PN
import geni.rspec.emulab.spectrum as spectrum


BIN_PATH = "/local/repository/bin"
ETC_PATH = "/local/repository/etc"
LOWLAT_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:U18LL-SRSLTE"
UBUNTU_IMG = "urn:publicid:IDN+emulab.net+image+emulab-ops//UBUNTU22-64-STD"
COTS_UE_IMG = "urn:publicid:IDN+emulab.net+image+PowderTeam:cots-jammy-image"
COMP_MANAGER_ID = "urn:publicid:IDN+emulab.net+authority+cm"
# old hash from branch bandwidth-testing-abs-sr-bsr-multiple_ue
#TODO: check if merged to develop or develop now supports multiple UEs
DEFAULT_NR_RAN_HASH = "1268b27c91be3a568dd352f2e9a21b3963c97432" # 2023.wk19
DEFAULT_NR_CN_HASH = "v1.5.0"

# DEFAULT_NR_RAN_HASH = "2024.w42" # 2023.wk19
# DEFAULT_NR_CN_HASH = "2024.w42"

# DEFAULT_NR_CN_HASH = "v2.1.0"
OAI_DEPLOY_SCRIPT = os.path.join(BIN_PATH, "deploy-oai.sh")
WIFI_AP_NODE_ID="ayaz-ap"
WIFI_CLIENT_NODE_ID="ayaz-laptop"


def UE_node_x310(idx, x310_radio):
	role = "ue"
	ue = request.RawPC("{}-ue-comp".format(x310_radio))
	ue.component_manager_id = COMP_MANAGER_ID
	ue.hardware_type = params.sdr_nodetype

	if params.sdr_compute_image:
		ue.disk_image = params.sdr_compute_image
	else:
		ue.disk_image = UBUNTU_IMG

	ue_radio_if = ue.addInterface("ue-usrp-if")
	ue_radio_if.addAddress(rspec.IPv4Address("192.168.40.1", "255.255.255.0"))

	radio_link = request.Link("radio-link-{}".format(idx))
	radio_link.bandwidth = 10*1000*1000
	radio_link.addInterface(ue_radio_if)

	radio = request.RawPC("{}-ue-sdr".format(x310_radio))
	radio.component_id = x310_radio
	radio.component_manager_id = COMP_MANAGER_ID
	radio_link.addNode(radio)

	if params.oai_ran_commit_hash:
		oai_ran_hash = params.oai_ran_commit_hash
	else:
		oai_ran_hash = DEFAULT_NR_RAN_HASH

	cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/common.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/tune-cpu.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd ="chmod +x /local/repository/bin/tune-sdr-iface.sh"
	ue.addService(rspec.Execute(shell="bash", command=cmd))

	cmd = '{} "{}" {}'.format(OAI_DEPLOY_SCRIPT, oai_ran_hash, role)
	ue.addService(rspec.Execute(shell="bash", command=cmd))
	ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-cpu.sh"))
	ue.addService(rspec.Execute(shell="bash", command="/local/repository/bin/tune-sdr-iface.sh"))


def alloc_wifi_resources():
    # Allocate WiFi utility node
    util = request.RawPC("wifi-util")
    util.component_manager_id = COMP_MANAGER_ID
    util.hardware_type = params.util_nodetype
    if params.util_image:
        util.disk_image = params.util_image
    else:
        util.disk_image = UBUNTU_IMG
    util_if = util.addInterface("util-if")
    util_if.addAddress(rspec.IPv4Address("192.168.1.10", "255.255.255.0"))

    # Allocate WiFi access point
    wifiap = request.RawPC("wifi-ap")
    wifiap.component_manager_id = COMP_MANAGER_ID
    wifiap.component_id = WIFI_AP_NODE_ID

    # Allocate WiFi client laptop
    wificl = request.RawPC("wifi-client")
    wificl.component_manager_id = COMP_MANAGER_ID
    wificl.component_id = WIFI_CLIENT_NODE_ID

    # Connect WiFi utility node, ap, and client to a LAN
    wifi_lan = request.LAN("wifi-util-lan")
    wifi_lan.bandwidth = 1*1000*1000 # 1 Gbps
    wifi_lan.addInterface(util_if)
    wifi_lan.addNode(wifiap)
    wifi_lan.addNode(wificl)


pc = portal.Context()

node_types = [
    ("d430", "Emulab, d430"),
    ("d740", "Emulab, d740"),
]

pc.defineParameter(
    name="alloc_wifi",
    description="Allocate WiFi resources (access point and utilty server)?",
    typ=portal.ParameterType.BOOLEAN,
    defaultValue=True
)

pc.defineParameter(
    name="sdr_nodetype",
    description="Type of compute node paired with the SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[1],
    legalValues=node_types
)

pc.defineParameter(
    name="cn_nodetype",
    description="Type of compute node to use for CN node (if included)",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[1],
    legalValues=node_types
)

pc.defineParameter(
    name="util_nodetype",
    description="Type of compute node to use for the WiFi utility server",
    typ=portal.ParameterType.STRING,
    defaultValue=node_types[0],
    legalValues=node_types
)

pc.defineParameter(
    name="oai_ran_commit_hash",
    description="Commit hash for OAI RAN",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="oai_cn_commit_hash",
    description="Commit hash for OAI (5G)CN",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="sdr_compute_image",
    description="Image to use for compute connected to SDRs",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

pc.defineParameter(
    name="util_image",
    description="Image to use for WiFi utility server",
    typ=portal.ParameterType.STRING,
    defaultValue="",
    advanced=True
)

indoor_ota_x310s = [
    ("ota-x310-1", "gNB"),
    ("ota-x310-2", "UE X310 #2"),
    ("ota-x310-3", "UE X310 #3"),
    ("ota-x310-4", "UE X310 #4"),
]

pc.defineParameter(
    name="x310_radio_UE",
    description="x310 Radio (for OAI UE 2)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[2],
    legalValues=indoor_ota_x310s
)

pc.defineParameter(
    name="x310_radio_UE",
    description="x310 Radio (for OAI UE 3)",
    typ=portal.ParameterType.STRING,
    defaultValue=indoor_ota_x310s[3],
    legalValues=indoor_ota_x310s
)


portal.context.defineStructParameter(
    "freq_ranges", "Frequency Ranges To Transmit In",
    defaultValue=[{"freq_min": 5730.0, "freq_max": 5770.0}],
    multiValue=True,
    min=0,
    multiValueTitle="Frequency ranges to be used for transmission.",
    members=[
        portal.Parameter(
            "freq_min",
            "Frequency Range Min",
            portal.ParameterType.BANDWIDTH,
            3550.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
        portal.Parameter(
            "freq_max",
            "Frequency Range Max",
            portal.ParameterType.BANDWIDTH,
            3600.0,
            longDescription="Values are rounded to the nearest kilohertz."
        ),
    ]
)

params = pc.bindParameters()
pc.verifyParameters()
request = pc.makeRequestRSpec()

role = "cn"
cn_node = request.RawPC("cn5g-docker-host")
cn_node.component_manager_id = COMP_MANAGER_ID
cn_node.hardware_type = params.cn_nodetype
cn_node.disk_image = UBUNTU_IMG
cn_if = cn_node.addInterface("cn-if")
cn_if.addAddress(rspec.IPv4Address("192.168.1.1", "255.255.255.0"))
cn_link = request.Link("cn-link")
# cn_link.bandwidth = 10*1000*1000
cn_link.addInterface(cn_if)

if params.oai_cn_commit_hash:
    oai_cn_hash = params.oai_cn_commit_hash
else:
    oai_cn_hash = DEFAULT_NR_CN_HASH

cmd ="chmod +x /local/repository/bin/deploy-oai.sh"
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

cmd ="chmod +x /local/repository/bin/common.sh"
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

cmd = "{} '{}' {}".format(OAI_DEPLOY_SCRIPT, oai_cn_hash, role)
cn_node.addService(rspec.Execute(shell="bash", command=cmd))

# Allocate wifi resources?
if params.alloc_wifi:
    alloc_wifi_resources()

# single x310 for gNB and UE for now
UE_node_x310(2, params.x310_radio_UE)
	
for frange in params.freq_ranges:
    request.requestSpectrum(frange.freq_min, frange.freq_max, 0)

# tour = IG.Tour()
# tour.Description(IG.Tour.MARKDOWN, tourDescription)
# tour.Instructions(IG.Tour.MARKDOWN, tourInstructions)
# request.addTour(tour)

pc.printRequestRSpec(request)
