#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/internet-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/applications-module.h"
#include "ns3/point-to-point-module.h"

#include <fstream>
#include <vector>
#include <string>
#include <cmath> // Needed for log10
#include <iostream> // Needed for std::cout

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Optic5GThesis");

// ==========================================
// GLOBAL METRICS (SINR TRACKING)
// ==========================================
double g_totalSinrLinear = 0.0;
uint64_t g_sinrCount = 0;

// FIXED: Removed 'std::string context' because we are using TraceConnectWithoutContext
void RsrpSinrCallback (uint16_t cellId, uint16_t rnti, double rsrp, double sinr, uint8_t componentCarrierId)
{
    // SINR from NS-3 is usually linear. We sum it linearly now and convert to dB later.
    g_totalSinrLinear += sinr;
    g_sinrCount++;
}

// ==========================================
// ENERGY MODEL
// ==========================================
double CalculateTotalEnergy(uint32_t activeTowers, double totalTxPowerDbm) {
    // Thesis Assumption: ~130W static power per active macro cell
    double staticConsumption = 130.0 * activeTowers; 
    return staticConsumption; 
}

int main (int argc, char *argv[])
{
    // 1. Simulation Setup
    double simTime = 20.0; 
    std::string activeTowerMask = ""; // Default empty = ALL ON (Baseline)
    
    CommandLine cmd;
    cmd.AddValue("simTime", "Simulation time in seconds", simTime);
    cmd.AddValue("mask", "Binary string to turn towers on/off", activeTowerMask);
    cmd.Parse (argc, argv);

    // 2. Setup LTE Helper with Urban Propagation
    Ptr<LteHelper> lteHelper = CreateObject<LteHelper> ();
    Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper> ();
    lteHelper->SetEpcHelper (epcHelper);

    // Use LogDistance for Urban Manila
    lteHelper->SetAttribute ("PathlossModel", StringValue ("ns3::LogDistancePropagationLossModel"));
    lteHelper->SetPathlossModelAttribute ("Exponent", DoubleValue (3.5)); 
    lteHelper->SetPathlossModelAttribute ("ReferenceLoss", DoubleValue (46.6)); 

    // 3. Setup Internet Core (EPC)
    Ptr<Node> pgw = epcHelper->GetPgwNode ();
    NodeContainer remoteHostContainer;
    remoteHostContainer.Create (1);
    Ptr<Node> remoteHost = remoteHostContainer.Get (0);
    InternetStackHelper internet;
    internet.Install (remoteHostContainer);

    PointToPointHelper p2ph;
    p2ph.SetDeviceAttribute ("DataRate", DataRateValue (DataRate ("100Gb/s")));
    p2ph.SetChannelAttribute ("Delay", TimeValue (Seconds (0.010)));
    NetDeviceContainer internetDevices = p2ph.Install (pgw, remoteHost);
    
    Ipv4AddressHelper ipv4h;
    ipv4h.SetBase ("1.0.0.0", "255.0.0.0");
    Ipv4InterfaceContainer internetIpIfaces = ipv4h.Assign (internetDevices);

    // 4. Load Towers from CSV
    NodeContainer enbNodes;
    NetDeviceContainer enbLteDevs;
    std::string csvPath = "data/real_towers_ns3.csv";
    std::ifstream file(csvPath);
    
    if (!file.is_open()) {
        NS_FATAL_ERROR("❌ Error: Cannot open " << csvPath);
    }
    
    std::string line;
    std::getline(file, line); // Skip Header

    size_t towerIndex = 0;
    int activeCount = 0;
    double totalTxPower = 0.0;

    while (std::getline(file, line)) {
        if (line.empty()) continue;
        
        // --- MASK CHECK LOGIC ---
        if (activeTowerMask.length() > 0 && towerIndex < activeTowerMask.length()) {
            if (activeTowerMask[towerIndex] == '0') {
                towerIndex++;
                continue; // Optimized OFF
            }
        }

        std::stringstream ss(line);
        std::string item;
        std::vector<double> rowData;
        while (std::getline(ss, item, ',')) {
            try { rowData.push_back(std::stod(item)); } catch (...) { rowData.push_back(0.0); }
        }

        if (rowData.size() < 5) continue; 

        double x = rowData[0];
        double y = rowData[1];
        double txPower = rowData[2]; 
        double bwMHz = rowData[4];

        Ptr<Node> thisNode = CreateObject<Node>();
        enbNodes.Add(thisNode); 

        Ptr<ListPositionAllocator> posAlloc = CreateObject<ListPositionAllocator>();
        posAlloc->Add(Vector(x, y, 30.0));
        MobilityHelper mob;
        mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mob.SetPositionAllocator(posAlloc);
        mob.Install(thisNode);

        Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(txPower));
        
        uint16_t rbs = 25;
        if (bwMHz >= 19.0) rbs = 100;
        else if (bwMHz >= 14.0) rbs = 75;
        else if (bwMHz >= 9.0) rbs = 50;

        lteHelper->SetEnbDeviceAttribute("DlBandwidth", UintegerValue(rbs));
        lteHelper->SetEnbDeviceAttribute("UlBandwidth", UintegerValue(rbs));
        lteHelper->SetEnbDeviceAttribute("DlEarfcn", UintegerValue(1650)); 
        lteHelper->SetEnbDeviceAttribute("UlEarfcn", UintegerValue(19650)); 

        NetDeviceContainer dev = lteHelper->InstallEnbDevice(NodeContainer(thisNode));
        enbLteDevs.Add(dev);

        activeCount++;
        totalTxPower += txPower;
        towerIndex++;
    }

    NS_LOG_UNCOND("--> Thesis Scenario: " << activeCount << " Active Towers");

    // 5. Create Users
    NodeContainer ueNodes;
    ueNodes.Create(250); 
    
    Config::SetDefault ("ns3::LteEnbRrc::SrsPeriodicity", UintegerValue (320));

    MobilityHelper ueMob;
    ueMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    Ptr<RandomRectanglePositionAllocator> uePos = CreateObject<RandomRectanglePositionAllocator>();
    uePos->SetAttribute("X", StringValue("ns3::UniformRandomVariable[Min=500.0|Max=20530.0]"));
    uePos->SetAttribute("Y", StringValue("ns3::UniformRandomVariable[Min=500.0|Max=70560.0]"));
    ueMob.SetPositionAllocator(uePos);
    ueMob.Install(ueNodes);

    NetDeviceContainer ueLteDevs = lteHelper->InstallUeDevice(ueNodes);
    internet.Install(ueNodes);
    Ipv4InterfaceContainer ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueLteDevs));
    lteHelper->AttachToClosestEnb(ueLteDevs, enbLteDevs);

    // --- CONNECT SINR LISTENER (MANUAL FIX) ---
    // FIXED: Removed the crashing 'Config::Connect' line.
    // Instead, we iterate through all UE devices and attach the listener manually to the PHY layer.
    for (uint32_t i = 0; i < ueLteDevs.GetN(); ++i)
    {
        Ptr<NetDevice> netDev = ueLteDevs.Get(i);
        Ptr<LteUeNetDevice> lteUeDev = DynamicCast<LteUeNetDevice>(netDev);
        if (lteUeDev)
        {
            // Get the PHY layer for Component Carrier 0 (Primary)
            Ptr<LteUePhy> phy = lteUeDev->GetPhy(); 
            if (phy)
            {
                // Connect without context because we are attaching directly to the object pointer
                phy->TraceConnectWithoutContext("ReportCurrentCellRsrpSinr", 
                                                MakeCallback(&RsrpSinrCallback));
            }
        }
    }

    // 6. Traffic Applications
    uint16_t port = 9;
    UdpServerHelper server (port);
    ApplicationContainer serverApps = server.Install (remoteHost);
    serverApps.Start (Seconds (3.0));
    serverApps.Stop (Seconds (simTime));

    UdpClientHelper client (internetIpIfaces.GetAddress (1), port);
    client.SetAttribute ("MaxPackets", UintegerValue (100000));
    client.SetAttribute ("Interval", TimeValue (MilliSeconds (20))); 
    client.SetAttribute ("PacketSize", UintegerValue (1024));
    ApplicationContainer clientApps = client.Install (ueNodes);
    clientApps.Start (Seconds (3.5));
    clientApps.Stop (Seconds (simTime));

    // 7. Metrics & Simulation
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll();

    NS_LOG_UNCOND("--> Simulation started. Running for " << simTime << " seconds...");
    Simulator::Stop(Seconds(simTime));
    Simulator::Run();

    // 8. Calculate Thesis Metrics
    monitor->CheckForLostPackets();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats();
    
    double totalRxBytes = 0;
    double totalThroughput = 0;
    double totalTxPackets = 0;
    double totalRxPackets = 0;
    
    for (auto const& [flowId, flowStats] : stats) {
        totalTxPackets += flowStats.txPackets;
        totalRxPackets += flowStats.rxPackets;
        totalRxBytes += flowStats.rxBytes;

        double flowDuration = flowStats.timeLastRxPacket.GetSeconds() - flowStats.timeFirstTxPacket.GetSeconds();
        if (flowDuration > 0) {
            totalThroughput += (flowStats.rxBytes * 8.0) / (flowDuration * 1000000.0); // Mbps
        }
    }

    double packetLossRatio = 0.0;
    if (totalTxPackets > 0) {
        packetLossRatio = ((totalTxPackets - totalRxPackets) / totalTxPackets) * 100.0;
    }

    double energyMetric = CalculateTotalEnergy(activeCount, totalTxPower);

    // CALCULATE AVERAGE SINR (dB)
    double averageSinrDb = -100.0; // Default low value
    if (g_sinrCount > 0) {
        double avgLinear = g_totalSinrLinear / g_sinrCount;
        // Avoid log(0)
        if (avgLinear > 0) {
            averageSinrDb = 10.0 * std::log10(avgLinear);
        }
    }

    NS_LOG_UNCOND("------------------------------------------------");
    NS_LOG_UNCOND("OPTIMIZATION RESULTS:");
    NS_LOG_UNCOND("Active Towers: " << activeCount);
    NS_LOG_UNCOND("Energy Score (Lower is better): " << energyMetric << " Watts (Est)");
    NS_LOG_UNCOND("System Throughput (Higher is better): " << totalThroughput << " Mbps");
    NS_LOG_UNCOND("Average SINR (Higher is better): " << averageSinrDb << " dB");
    NS_LOG_UNCOND("Packet Loss Ratio (Lower is better): " << packetLossRatio << " %");
    NS_LOG_UNCOND("------------------------------------------------");

    monitor->SerializeToXmlFile("manila_5g_results.xml", true, true);

    Simulator::Destroy();
    return 0;
}
