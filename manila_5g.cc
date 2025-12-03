#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/lte-module.h"
#include "ns3/internet-module.h"
#include "ns3/flow-monitor-module.h"
#include "ns3/applications-module.h"
#include "ns3/point-to-point-module.h" // Fixed: Added missing header

#include <fstream>
#include <vector>
#include <string>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Optic5GThesis");

// --- THESIS HELPER: ENERGY MODEL ---
// Simplified power consumption model for 5G Base Stations
double CalculateTotalEnergy(uint32_t activeTowers, double totalTxPowerDbm) {
    // Thesis Assumption: Baseline static power consumption per active Macro BS.
    // In a real scenario, this would be dynamic based on load.
    // We assume ~130W static power for a standard active macro cell.
    double staticConsumption = 130.0 * activeTowers; 
    return staticConsumption; 
}

int main (int argc, char *argv[])
{
    // 1. Simulation Setup
    // Increased to 20s to allow LTE connection setup and stable throughput measurement
    double simTime = 20.0; 
    std::string activeTowerMask = ""; // Used for Quantum Optimization (e.g., "10110")
    
    CommandLine cmd;
    cmd.AddValue("simTime", "Simulation time in seconds", simTime);
    cmd.AddValue("mask", "Binary string to turn towers on/off (e.g., 10110)", activeTowerMask);
    cmd.Parse (argc, argv);

    // 2. Setup LTE Helper with Urban Propagation
    Ptr<LteHelper> lteHelper = CreateObject<LteHelper> ();
    Ptr<PointToPointEpcHelper> epcHelper = CreateObject<PointToPointEpcHelper> ();
    lteHelper->SetEpcHelper (epcHelper);

    // Use LogDistance for Urban Manila environment (Better than Friis for cities)
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
        NS_FATAL_ERROR("❌ Error: Cannot open " << csvPath << ". Make sure it is in the data/ folder.");
    }
    
    std::string line;
    std::getline(file, line); // Skip CSV Header

    size_t towerIndex = 0; // unsigned integer to fix warning
    int activeCount = 0;
    double totalTxPower = 0.0;

    // --- Tower Creation Loop ---
    while (std::getline(file, line)) {
        if (line.empty()) continue;
        
        // Thesis Optimization Logic: Check Mask
        if (activeTowerMask.length() > 0 && towerIndex < activeTowerMask.length()) {
            if (activeTowerMask[towerIndex] == '0') {
                towerIndex++;
                continue; // Skip creating this tower (It is turned OFF by Quantum Algo)
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
        posAlloc->Add(Vector(x, y, 30.0)); // Assume 30m tower height
        MobilityHelper mob;
        mob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
        mob.SetPositionAllocator(posAlloc);
        mob.Install(thisNode);

        // Global config to handle different TxPowers per node
        Config::SetDefault("ns3::LteEnbPhy::TxPower", DoubleValue(txPower));
        
        // Bandwidth logic
        uint16_t rbs = 25;
        if (bwMHz >= 19.0) rbs = 100;
        else if (bwMHz >= 14.0) rbs = 75;
        else if (bwMHz >= 9.0) rbs = 50;

        lteHelper->SetEnbDeviceAttribute("DlBandwidth", UintegerValue(rbs));
        lteHelper->SetEnbDeviceAttribute("UlBandwidth", UintegerValue(rbs));
        lteHelper->SetEnbDeviceAttribute("DlEarfcn", UintegerValue(1650)); // Band 3
        lteHelper->SetEnbDeviceAttribute("UlEarfcn", UintegerValue(19650)); 

        NetDeviceContainer dev = lteHelper->InstallEnbDevice(NodeContainer(thisNode));
        enbLteDevs.Add(dev);

        activeCount++;
        totalTxPower += txPower;
        towerIndex++;
    }

    NS_LOG_UNCOND("--> Thesis Scenario: " << activeCount << " Active Towers");

    // 5. Create Users (The "Demand")
    NodeContainer ueNodes;
    ueNodes.Create(500); // Simulating 500 active users
    MobilityHelper ueMob;
    ueMob.SetMobilityModel("ns3::ConstantPositionMobilityModel");
    
    // IMPORTANT: Ensure these coordinates match your CSV data area!
    // Updated bounds based on your real data (rounded up slightly)
    Ptr<RandomRectanglePositionAllocator> uePos = CreateObject<RandomRectanglePositionAllocator>();
    uePos->SetAttribute("X", StringValue("ns3::UniformRandomVariable[Min=500.0|Max=20530.0]"));
    uePos->SetAttribute("Y", StringValue("ns3::UniformRandomVariable[Min=500.0|Max=70560.0]"));
    ueMob.SetPositionAllocator(uePos);
    ueMob.Install(ueNodes);

    NetDeviceContainer ueLteDevs = lteHelper->InstallUeDevice(ueNodes);
    internet.Install(ueNodes);
    Ipv4InterfaceContainer ueIpIface = epcHelper->AssignUeIpv4Address (NetDeviceContainer (ueLteDevs));
    lteHelper->AttachToClosestEnb(ueLteDevs, enbLteDevs);

    // 6. Traffic Applications
    uint16_t port = 9;
    
    // Server sends data (Downlink) starting at 3.0s
    UdpServerHelper server (port);
    ApplicationContainer serverApps = server.Install (remoteHost);
    serverApps.Start (Seconds (3.0));
    serverApps.Stop (Seconds (simTime));

    // Clients receive data starting at 3.5s
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

        // Accurate Throughput: Calculate only for the active flow duration
        double flowDuration = flowStats.timeLastRxPacket.GetSeconds() - flowStats.timeFirstTxPacket.GetSeconds();
        if (flowDuration > 0) {
            totalThroughput += (flowStats.rxBytes * 8.0) / (flowDuration * 1000000.0); // Mbps
        }
    }

    // Packet Loss Calculation
    double packetLossRatio = 0.0;
    if (totalTxPackets > 0) {
        packetLossRatio = ((totalTxPackets - totalRxPackets) / totalTxPackets) * 100.0;
    }

    double energyMetric = CalculateTotalEnergy(activeCount, totalTxPower);

    NS_LOG_UNCOND("------------------------------------------------");
    NS_LOG_UNCOND("OPTIMIZATION RESULTS:");
    NS_LOG_UNCOND("Active Towers: " << activeCount);
    NS_LOG_UNCOND("Energy Score (Lower is better): " << energyMetric << " Watts (Est)");
    NS_LOG_UNCOND("System Throughput (Higher is better): " << totalThroughput << " Mbps");
    NS_LOG_UNCOND("Packet Loss Ratio (Lower is better): " << packetLossRatio << " %");
    NS_LOG_UNCOND("------------------------------------------------");

    // Save detailed stats to XML for graphing
    monitor->SerializeToXmlFile("manila_5g_results.xml", true, true);

    Simulator::Destroy();
    return 0;
}
