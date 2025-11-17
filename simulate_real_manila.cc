/* simulate_real_manila_mmwave.cc
   Place in ns3-mmwave/scratch/
   Build with: ./ns3 build
   Run with:   ./ns3 run scratch/simulate_real_manila_mmwave
   Example:
     ./ns3 run scratch/simulate_real_manila_mmwave --siteFile=data/real_towers_ns3.csv --numUes=500 --simTime=30
*/

#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/internet-module.h"
#include "ns3/mobility-module.h"
#include "ns3/point-to-point-module.h"
#include "ns3/applications-module.h"
#include "ns3/flow-monitor-module.h"

// mmWave / EPC helper headers (module names may vary by mmwave extension)
#include "ns3/mmwave-helper.h"
#include "ns3/epc-helper.h"
#include "ns3/point-to-point-epc-helper.h"

#include <fstream>
#include <sstream>
#include <limits>
#include <cstdlib>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE("SimulateRealManilaMmwave");

struct Site {
  double x_m;        // x in meters (simulation coordinates)
  double y_m;        // y in meters (simulation coordinates)
  double txPower;    // dBm
  double freqGHz;
  double bwMHz;
  double radius;
  std::string rawLine; // for debugging
};

// Simple helper: trim
static inline std::string trim(const std::string &s) {
  auto b = s.find_first_not_of(" \t\r\n\"");
  if (b == std::string::npos) return "";
  auto e = s.find_last_not_of(" \t\r\n\"");
  return s.substr(b, e - b + 1);
}

// Read CSV and detect columns. Accepts:
// - x,y,txPower_dBm,frequency_GHz,bandwidth_MHz,radius_m   (x,y already in meters)
// - lon,lat,txPower_dBm,...  (lon,lat in degrees; will convert to meters)
std::vector<Site> ReadSites(const std::string &csvFile) {
  std::vector<Site> sites;
  std::ifstream f(csvFile.c_str());
  if (!f.is_open()) {
    NS_FATAL_ERROR("Cannot open " << csvFile);
  }

  std::string header;
  if (!std::getline(f, header)) {
    NS_FATAL_ERROR("Empty CSV file: " << csvFile);
  }

  // parse header
  std::vector<std::string> cols;
  {
    std::stringstream ss(header);
    std::string tok;
    while (std::getline(ss, tok, ',')) cols.push_back(trim(tok));
  }
  // normalize header names (lowercase)
  for (auto &c : cols) {
    for (auto &ch : c) ch = std::tolower(ch);
  }

  bool has_xy = false, has_lonlat = false;
  int idx_x = -1, idx_y = -1, idx_lon = -1, idx_lat = -1;
  int idx_tx = -1, idx_freq = -1, idx_bw = -1, idx_r = -1;

  for (size_t i = 0; i < cols.size(); ++i) {
    const std::string &c = cols[i];
    if (c == "x" || c == "x_m" || c == "x_meters") { idx_x = i; has_xy = true; }
    if (c == "y" || c == "y_m" || c == "y_meters") { idx_y = i; has_xy = true; }
    if (c == "lon" || c == "longitude") { idx_lon = i; has_lonlat = true; }
    if (c == "lat" || c == "latitude") { idx_lat = i; has_lonlat = true; }
    if (c == "txpower_dbm" || c == "tx_power_dbm" || c == "txpower" || c == "tx_power") idx_tx = i;
    if (c == "frequency_ghz" || c == "frequency" || c == "freq_ghz") idx_freq = i;
    if (c == "bandwidth_mhz" || c == "bandwidth" || c == "bw_mhz") idx_bw = i;
    if (c == "radius_m" || c == "radius") idx_r = i;
  }

  // read all raw lines first to compute mean lat/lon if needed
  std::vector<std::vector<std::string>> rows;
  std::string line;
  while (std::getline(f, line)) {
    if (line.find_first_not_of(" \t\r\n") == std::string::npos) continue;
    // split respecting simple CSV rules (no robust CSV lib used to keep ns-3 compile friendly)
    std::vector<std::string> toks;
    std::stringstream ss(line);
    std::string tok;
    while (std::getline(ss, tok, ',')) toks.push_back(trim(tok));
    rows.push_back(toks);
  }
  f.close();

  // If lon/lat and conversion needed, compute mean lat for projection center
  double meanLat = 0.0, meanLon = 0.0;
  if (has_lonlat) {
    int count = 0;
    for (auto &toks : rows) {
      if ((int)toks.size() > idx_lon && (int)toks.size() > idx_lat) {
        try {
          double lon = std::stod(toks[idx_lon]);
          double lat = std::stod(toks[idx_lat]);
          meanLon += lon; meanLat += lat; ++count;
        } catch (...) { continue; }
      }
    }
    if (count > 0) { meanLat /= count; meanLon /= count; }
    else { meanLat = 14.59; meanLon = 120.98; } // fallback to Manila center
  }

  // meters per degree approximations (latitude ~111320 m/deg)
  const double meters_per_deg_lat = 111320.0;
  auto meters_per_deg_lon = [&](double lat_deg) {
    return meters_per_deg_lat * std::cos(lat_deg * M_PI / 180.0);
  };

  // parse each row into Site
  for (auto &toks : rows) {
    Site s;
    s.x_m = 0.0; s.y_m = 0.0;
    s.txPower = 20.0; s.freqGHz = 3.5; s.bwMHz = 100.0; s.radius = 250.0;
    s.rawLine = "";

    // try x,y first if present
    bool parsed = false;
    try {
      if (has_xy && (int)toks.size() > idx_x && (int)toks.size() > idx_y) {
        double xv = std::stod(toks[idx_x]);
        double yv = std::stod(toks[idx_y]);
        // Heuristic: if xv, yv look like degrees (lat bounds), treat them as lon/lat and convert
        if (std::abs(yv) <= 90.0 && std::abs(xv) <= 180.0) {
          // (xv=lon, yv=lat) -> convert to meters centered at meanLat/meanLon
          double meters_per_lon = meters_per_deg_lon(meanLat);
          s.x_m = (xv - meanLon) * meters_per_lon;
          s.y_m = (yv - meanLat) * meters_per_deg_lat;
        } else {
          // assume already meters
          s.x_m = xv;
          s.y_m = yv;
        }
        parsed = true;
      } else if (has_lonlat && (int)toks.size() > idx_lon && (int)toks.size() > idx_lat) {
        double lon = std::stod(toks[idx_lon]);
        double lat = std::stod(toks[idx_lat]);
        double meters_per_lon = meters_per_deg_lon(meanLat);
        s.x_m = (lon - meanLon) * meters_per_lon;
        s.y_m = (lat - meanLat) * meters_per_deg_lat;
        parsed = true;
      }
    } catch (...) {
      parsed = false;
    }

    // try remaining attributes (txPower etc)
    try {
      if (idx_tx >= 0 && (int)toks.size() > idx_tx) {
        s.txPower = std::stod(toks[idx_tx]);
      }
      if (idx_freq >= 0 && (int)toks.size() > idx_freq) {
        s.freqGHz = std::stod(toks[idx_freq]);
      }
      if (idx_bw >= 0 && (int)toks.size() > idx_bw) {
        s.bwMHz = std::stod(toks[idx_bw]);
      }
      if (idx_r >= 0 && (int)toks.size() > idx_r) {
        s.radius = std::stod(toks[idx_r]);
      }
    } catch (...) {
      // ignore and use defaults
    }

    // If parsing failed (malformed row or missing coords), skip row
    if (!parsed) continue;

    // store original raw for debugging
    // reconstruct raw
    {
      std::ostringstream os;
      for (size_t i = 0; i < toks.size(); ++i) {
        if (i) os << ",";
        os << toks[i];
      }
      s.rawLine = os.str();
    }
    sites.push_back(s);
  }

  // Now sites currently have coordinates in meters but centered on meanLat/meanLon (offsets around 0).
  // ns-3 prefers positive coordinates (not required, but nicer). Shift so min is 0 + small margin.
  if (!sites.empty()) {
    double minx = std::numeric_limits<double>::infinity();
    double miny = std::numeric_limits<double>::infinity();
    for (auto &s : sites) { minx = std::min(minx, s.x_m); miny = std::min(miny, s.y_m); }
    double pad = 200.0; // 200 m padding
    // shift by -(min) + pad
    for (auto &s : sites) {
      s.x_m = s.x_m - minx + pad;
      s.y_m = s.y_m - miny + pad;
    }
  }

  return sites;
}

int main (int argc, char *argv[]) {
  LogComponentEnable("SimulateRealManilaMmwave", LOG_LEVEL_INFO);

  std::string siteFile = "data/real_towers_ns3.csv";
  uint32_t numUes = 1000;
  double simTime = 40.0;
  uint32_t startFlowTime = 2;

  CommandLine cmd;
  cmd.AddValue("siteFile", "CSV file containing x,y or lon,lat + other optional columns", siteFile);
  cmd.AddValue("numUes", "Number of UEs to create", numUes);
  cmd.AddValue("simTime", "Simulation time (s)", simTime);
  cmd.Parse(argc, argv);

  std::vector<Site> sites = ReadSites(siteFile);
  NS_LOG_INFO("Loaded " << sites.size() << " sites from " << siteFile);

  if (sites.empty()) {
    NS_FATAL_ERROR("No sites loaded. Check " << siteFile);
  }

  NodeContainer enbNodes;
  enbNodes.Create(sites.size());

  NodeContainer ueNodes;
  ueNodes.Create(numUes);

  // Mobility for eNBs
  MobilityHelper mobility;
  Ptr<ListPositionAllocator> enbPosAlloc = CreateObject<ListPositionAllocator>();
  for (auto &s : sites) {
    enbPosAlloc->Add(Vector(s.x_m, s.y_m, 10.0));
  }
  mobility.SetPositionAllocator(enbPosAlloc);
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(enbNodes);

  // Determine bounding box for UEs and scatter them uniformly inside
  double minx = std::numeric_limits<double>::infinity();
  double maxx = -std::numeric_limits<double>::infinity();
  double miny = std::numeric_limits<double>::infinity();
  double maxy = -std::numeric_limits<double>::infinity();
  for (auto &s : sites) {
    minx = std::min(minx, s.x_m); maxx = std::max(maxx, s.x_m);
    miny = std::min(miny, s.y_m); maxy = std::max(maxy, s.y_m);
  }
  double padx = (maxx - minx) * 0.05 + 50.0;
  double pady = (maxy - miny) * 0.05 + 50.0;
  minx -= padx; maxx += padx; miny -= pady; maxy += pady;

  // UE positions
  Ptr<ListPositionAllocator> uePosAlloc = CreateObject<ListPositionAllocator>();
  std::srand(12345);
  for (uint32_t i = 0; i < numUes; ++i) {
    double x = minx + (double)(std::rand()) / RAND_MAX * (maxx - minx);
    double y = miny + (double)(std::rand()) / RAND_MAX * (maxy - miny);
    uePosAlloc->Add(Vector(x, y, 1.5));
  }
  mobility.SetPositionAllocator(uePosAlloc);
  mobility.SetMobilityModel("ns3::ConstantPositionMobilityModel");
  mobility.Install(ueNodes);

  // mmWave + EPC setup
  Ptr<ns3::mmwave::MmWaveHelper> mmwaveHelper = CreateObject<ns3::mmwave::MmWaveHelper>();
  Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper>();
  mmwaveHelper->SetEpcHelper(epcHelper);

  // Install mmWave devices on eNBs
  NetDeviceContainer enbDevs;
  for (uint32_t i = 0; i < enbNodes.GetN(); ++i) {
    NetDeviceContainer nd = mmwaveHelper->InstallEnbDevice(enbNodes.Get(i));
    enbDevs.Add(nd);
  }
  if (enbDevs.GetN() == 0) {
    NS_FATAL_ERROR("No eNB devices installed. Check mmWave module and enb installation.");
  }

  // Install UE devices
  NetDeviceContainer ueDevs = mmwaveHelper->InstallUeDevice(ueNodes);
  if (ueDevs.GetN() == 0) {
    NS_FATAL_ERROR("No UE devices installed.");
  }

  // IP stack and IPv4 allocation via EPC
  InternetStackHelper internet;
  internet.Install(ueNodes);
  epcHelper->AssignUeIpv4Address(ueDevs);

  // Attach UEs to closest eNB automatically
  mmwaveHelper->AttachToClosestEnb(ueDevs, enbDevs);

  // Remote host via EPC PGW
  Ptr<Node> pgw = epcHelper->GetPgwNode();
  NodeContainer remoteHostContainer;
  remoteHostContainer.Create(1);
  Ptr<Node> remoteHost = remoteHostContainer.Get(0);
  InternetStackHelper internet2;
  internet2.Install(remoteHostContainer);

  PointToPointHelper p2ph;
  p2ph.SetDeviceAttribute("DataRate", DataRateValue(DataRate("10Gb/s")));
  p2ph.SetChannelAttribute("Delay", TimeValue(Seconds(0.01)));
  NetDeviceContainer p2pDevices = p2ph.Install(pgw, remoteHost);

  Ipv4AddressHelper ipv4h;
  ipv4h.SetBase("1.0.0.0", "255.0.0.0");
  Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign(p2pDevices);
  Ipv4Address remoteHostAddr = internetIpIfaces.GetAddress(1);

  // UDP server/client
  uint16_t serverPort = 50000;
  UdpServerHelper server(serverPort);
  ApplicationContainer serverApps = server.Install(remoteHost);
  serverApps.Start(Seconds(1.0));
  serverApps.Stop(Seconds(simTime + 1.0));

  uint32_t numClients = std::min<uint32_t>(numUes, 600);
  for (uint32_t i = 0; i < numClients; ++i) {
    OnOffHelper client("ns3::UdpSocketFactory", InetSocketAddress(remoteHostAddr, serverPort));
    client.SetAttribute("OnTime", StringValue("ns3::ConstantRandomVariable[Constant=1]"));
    client.SetAttribute("OffTime", StringValue("ns3::ConstantRandomVariable[Constant=0]"));
    client.SetAttribute("DataRate", DataRateValue(DataRate("2Mbps")));
    client.SetAttribute("PacketSize", UintegerValue(1024));
    ApplicationContainer clientApps = client.Install(ueNodes.Get(i));
    clientApps.Start(Seconds(startFlowTime + 0.01*i/100.0));
    clientApps.Stop(Seconds(simTime));
  }

  // FlowMonitor
  FlowMonitorHelper flowmon;
  Ptr<FlowMonitor> monitor = flowmon.InstallAll();

  Simulator::Stop(Seconds(simTime + 1.0));
  Simulator::Run();

  // Flow stats
  monitor->CheckForLostPackets();
  Ptr<Ipv4FlowClassifier> classifier = DynamicCast<Ipv4FlowClassifier>(flowmon.GetClassifier());

  // Ensure outputs dir exists
  system("mkdir -p outputs");

  std::ofstream flowOut("outputs/flow_stats.csv");
  flowOut << "flowId,srcAddr,dstAddr,txBytes,rxBytes,txPackets,rxPackets,throughput_mbps,delay_s,jitter_s\n";

  std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();
  for (const auto& flowPair : stats) {
    FlowId flowId = flowPair.first;
    const FlowMonitor::FlowStats &fs = flowPair.second;
    Ipv4FlowClassifier::FiveTuple t = classifier->FindFlow(flowId);

    double throughput_mbps = 0.0;
    if (simTime > 0.0) {
      throughput_mbps = (fs.rxBytes * 8.0) / (simTime * 1e6); // Mbps
    }

    double delay_s = 0.0;
    double jitter_s = 0.0;
    if (fs.rxPackets > 0) {
      delay_s = fs.delaySum.GetSeconds() / fs.rxPackets;
      jitter_s = fs.jitterSum.GetSeconds() / fs.rxPackets;
    }

    flowOut << flowId << ","
            << t.sourceAddress << ","
            << t.destinationAddress << ","
            << fs.txBytes << ","
            << fs.rxBytes << ","
            << fs.txPackets << ","
            << fs.rxPackets << ","
            << throughput_mbps << ","
            << delay_s << ","
            << jitter_s << "\n";
  }

  flowOut.close();

  Simulator::Destroy();
  NS_LOG_INFO("Simulation finished. Flow stats written to outputs/flow_stats.csv");
  return 0;
}
