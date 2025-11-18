/* simulate_real_manila_mmwave_full.cc
   Full-Manila OPTIC-5G mmWave run (heavy).
   - Uses all sites in CSV
   - Higher UE counts, larger flows
   - Designed for powerful machines (>= 32GB recommended)
   Build: ./ns3 build
   Run example:
     ./ns3 run scratch/simulate_real_manila_mmwave_full -- --siteFile=data/real_towers_ns3.csv --numUes=5000 --simTime=120
*/

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"

// mmWave / EPC helper headers
#include "ns3/mmwave-helper.h"
#include "ns3/point-to-point-epc-helper.h"

#include <fstream>
#include <sstream>
#include <vector>
#include <string>
#include <limits>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SimulateRealManilaMmwaveFull");

static std::vector<std::vector<std::string>> ReadCsvRows(const std::string &file) {
  std::vector<std::vector<std::string>> rows;
  std::ifstream in(file.c_str());
  if (!in.is_open()) return rows;
  std::string line;
  if (!std::getline(in, line)) return rows;
  bool headerLooksLikeHeader = false;
  for (char c : line) if (std::isalpha((unsigned char)c)) { headerLooksLikeHeader = true; break; }
  if (!headerLooksLikeHeader) {
    std::vector<std::string> toks;
    std::stringstream ss(line); std::string tok;
    while (std::getline(ss, tok, ',')) toks.push_back(tok);
    rows.push_back(toks);
  }
  while (std::getline(in, line)) {
    if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
    std::vector<std::string> toks;
    std::stringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, ',')) toks.push_back(tok);
    rows.push_back(toks);
  }
  in.close();
  return rows;
}

struct Site { double x; double y; double tx; double radius; };

static std::vector<Site> LoadSitesFromCsvAll(const std::string &csvFile) {
  std::vector<Site> sites;
  auto rows = ReadCsvRows(csvFile);
  for (auto &r : rows) {
    if (r.size() < 3) continue;
    double lat=0, lon=0; bool ok=false;
    try { lon = std::stod(r[2]); lat = std::stod(r[1]); ok = true; } catch(...) { ok=false; }
    if (!ok) {
      try { double xv = std::stod(r[0]); double yv = std::stod(r[1]); sites.push_back({xv,yv,20.0,200.0}); }
      catch(...) { continue; }
    } else {
      const double lat0 = 14.59; const double lon0 = 120.98;
      const double meters_per_deg_lat = 111320.0;
      double meters_per_deg_lon = meters_per_deg_lat * std::cos(lat0 * M_PI / 180.0);
      double x = (lon - lon0) * meters_per_deg_lon;
      double y = (lat - lat0) * meters_per_deg_lat;
      sites.push_back({x,y,43.0,250.0});
    }
  }
  if (!sites.empty()) {
    double minx = std::numeric_limits<double>::infinity(), miny = std::numeric_limits<double>::infinity();
    for (auto &s: sites) { if (s.x < minx) minx = s.x; if (s.y < miny) miny = s.y; }
    double pad = 200.0;
    for (auto &s: sites) { s.x = s.x - minx + pad; s.y = s.y - miny + pad; }
  }
  return sites;
}

int main(int argc, char *argv[]) {
  std::string siteFile = "data/real_towers_ns3.csv";
  uint32_t numUes = 2000;
  double simTime = 60.0;

  CommandLine cmd;
  cmd.AddValue("siteFile", "CSV with tower coords (address,lat,lon or x,y)", siteFile);
  cmd.AddValue("numUes", "Number of UE nodes", numUes);
  cmd.AddValue("simTime", "Simulation time (s)", simTime);
  cmd.Parse(argc, argv);

  LogComponentEnable("SimulateRealManilaMmwaveFull", LOG_LEVEL_INFO);
  NS_LOG_INFO("Loading sites from " << siteFile);

  auto sites = LoadSitesFromCsvAll(siteFile);
  NS_LOG_INFO("Loaded " << sites.size() << " sites");

  if (sites.empty()) NS_FATAL_ERROR("No sites loaded.");

  NodeContainer enbNodes; enbNodes.Create(sites.size());
  NodeContainer ueNodes; ueNodes.Create(numUes);

  MobilityHelper mobility;
  Ptr<ListPositionAllocator> enbAlloc = CreateObject<ListPositionAllocator>();
  for (auto &s : sites) enbAlloc->Add(Vector(s.x, s.y, 20.0));
  mobility.SetPositionAllocator(enbAlloc);
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(enbNodes);

  double minx = std::numeric_limits<double>::infinity(), maxx=-1e9, miny=1e9, maxy=-1e9;
  for (auto &s : sites) { minx = std::min(minx, s.x); maxx = std::max(maxx, s.x); miny = std::min(miny, s.y); maxy = std::max(maxy, s.y); }
  double padx = (maxx-minx)*0.05 + 50.0, pady = (maxy-miny)*0.05 + 50.0;
  minx -= padx; maxx += padx; miny -= pady; maxy += pady;

  Ptr<ListPositionAllocator> ueAlloc = CreateObject<ListPositionAllocator>();
  for (uint32_t i=0;i<numUes;i++) {
    double x = minx + (double)std::rand() / RAND_MAX * (maxx-minx);
    double y = miny + (double)std::rand() / RAND_MAX * (maxy-miny);
    ueAlloc->Add(Vector(x,y,1.5));
  }
  mobility.SetPositionAllocator(ueAlloc);
  mobility.Install(ueNodes);

  Ptr<ns3::mmwave::MmWaveHelper> mmwaveHelper = CreateObject<ns3::mmwave::MmWaveHelper>();
  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper>();
  mmwaveHelper->SetEpcHelper(epcHelper);

  NetDeviceContainer enbDevs;
  for (uint32_t i=0;i<enbNodes.GetN(); ++i) {
    NetDeviceContainer d = mmwaveHelper->InstallEnbDevice(enbNodes.Get(i));
    enbDevs.Add(d);
  }
  if (enbDevs.GetN() == 0) NS_FATAL_ERROR("No eNB devices installed");

  NetDeviceContainer ueDevs = mmwaveHelper->InstallUeDevice(ueNodes);
  if (ueDevs.GetN() == 0) NS_FATAL_ERROR("No UE devices installed");

  InternetStackHelper internet;
  internet.Install(ueNodes);
  epcHelper->AssignUeIpv4Address(ueDevs);

  mmwaveHelper->AttachToClosestEnb(ueDevs, enbDevs);

  Ptr<Node> pgw = epcHelper->GetPgwNode();
  NodeContainer remoteHostContainer; remoteHostContainer.Create(1);
  Ptr<Node> remoteHost = remoteHostContainer.Get(0);
  InternetStackHelper internet2; internet2.Install(remoteHostContainer);

  PointToPointHelper p2ph; p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("10Gb/s"))); p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(0.01)));
  NetDeviceContainer p2pDevices = p2ph.Install(pgw, remoteHost);

  Ipv4AddressHelper ipv4h; ipv4h.SetBase("172.16.0.0","255.240.0.0"); // bigger private block
  Ipv4InterfaceContainer ifs = ipv4h.Assign(p2pDevices);
  Ipv4Address remoteHostAddr = ifs.GetAddress(1);

  // Server
  uint16_t serverPort = 60000;
  UdpServerHelper server(serverPort);
  ApplicationContainer serverApps = server.Install(remoteHost);
  serverApps.Start(Seconds(1.0));
  serverApps.Stop(Seconds(simTime + 1.0));

  // Clients: heavy flow load (use fewer active clients than UEs for performance)
  uint32_t numClients = std::min<uint32_t>(numUes, 1500);
  for (uint32_t i=0;i<numClients;i++) {
    OnOffHelper client("ns3::UdpSocketFactory", InetSocketAddress(remoteHostAddr, serverPort));
    client.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    client.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
    client.SetAttribute("DataRate", DataRateValue(DataRate("2Mbps")));
    client.SetAttribute("PacketSize", UintegerValue(1400));
    ApplicationContainer apps = client.Install(ueNodes.Get(i));
    apps.Start(Seconds(2.0 + 0.001*i));
    apps.Stop(Seconds(simTime));
  }

  // FlowMonitor
  FlowMonitorHelper flowmon; Ptr<FlowMonitor> monitor = flowmon.InstallAll();

  Simulator::Stop(Seconds(simTime + 1.0));
  Simulator::Run();

  monitor->CheckForLostPackets();
  Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowmon.GetClassifier());

  system("mkdir -p outputs");
  std::ofstream flowOut("outputs/full_flow_stats.csv");
  flowOut << "flowId,src,dst,txBytes,rxBytes,txPackets,rxPackets,throughput_mbps\n";

  auto stats = monitor->GetFlowStats();
  for (auto &p : stats) {
    FlowId fid = p.first;
    const FlowMonitor::FlowStats &fs = p.second;
    Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(fid);
    double throughput = (fs.rxBytes * 8.0) / (simTime * 1e6);
    flowOut << fid << "," << t.sourceAddress << "," << t.destinationAddress << "," << fs.txBytes << "," << fs.rxBytes << "," << fs.txPackets << "," << fs.rxPackets << "," << throughput << "\n";
  }
  flowOut.close();

  Simulator::Destroy();
  NS_LOG_INFO("Finished Full Manila simulation. Wrote outputs/full_flow_stats.csv");
  return 0;
}
