#include "ns3/core-module.h"
#include "ns3/network-module.h"
#include "ns3/mobility-module.h"
#include "ns3/wifi-module.h"
#include "ns3/internet-module.h"
#include "ns3/applications-module.h"
#include "ns3/antenna-module.h"
#include "ns3/flow-monitor-module.h"
#include <iostream>
#include <string>
#include <cmath>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("Optic5GPupTestbed");

// ==========================================
// NEW: Global variables to track SINR
// ==========================================
double globalTotalSinrDb = 0.0;
uint32_t globalSinrSamples = 0;

// NEW: Trace Callback to extract Signal and Noise per packet
void MonitorSnifferRxCallback(std::string context, Ptr<const Packet> packet, 
                              uint16_t channelFreqMhz, WifiTxVector txVector, 
                              MpduInfo aMpdu, SignalNoiseDbm signalNoise, uint16_t staId) 
{
    double signal = signalNoise.signal; // Signal strength in dBm
    double noise = signalNoise.noise;   // Noise floor in dBm
    double sinrDb = signal - noise;     // SINR calculation
    
    globalTotalSinrDb += sinrDb;
    globalSinrSamples++;
}

// Energy model: 10.5 Watts per active TP-Link router
double CalculateTestbedEnergy(int activeNodes) { 
    return activeNodes * 10.5; 
}

int main (int argc, char *argv[]) {
    double simTime = 10.0;
    std::string activeMask = "11111111111111111"; 
    uint32_t numUsers = 20; 

    CommandLine cmd;
    cmd.AddValue ("mask", "17-bit binary string", activeMask);
    cmd.Parse (argc, argv);

    NodeContainer apNodes; apNodes.Create (17);
    NodeContainer userNodes; userNodes.Create (numUsers);

    // ==========================================
    // 1. Custom Channel (Line-of-Sight Physics)
    // ==========================================
    YansWifiChannelHelper channel; 
    channel.SetPropagationDelay ("ns3::ConstantSpeedPropagationDelayModel");
    channel.AddPropagationLoss ("ns3::LogDistancePropagationLossModel", 
                                "Exponent", DoubleValue (2.2)); 
    
    YansWifiPhyHelper phy;
    phy.SetChannel (channel.Create ());

    WifiHelper wifi;
    wifi.SetStandard (WIFI_STANDARD_80211ac);
    wifi.SetRemoteStationManager ("ns3::ConstantRateWifiManager",
                                  "DataMode", StringValue ("VhtMcs0"), // Robust BPSK
                                  "ControlMode", StringValue ("VhtMcs0"));
    
    WifiMacHelper mac;
    mac.SetType ("ns3::AdhocWifiMac");

    // ==========================================
    // 2. Geospatial AP Topologies (PUP Sta. Mesa)
    // ==========================================
    MobilityHelper apMobility;
    Ptr<ListPositionAllocator> apPosAlloc = CreateObject<ListPositionAllocator> ();
    
    // Coordinates (X, Y) in meters from the campus center (0,0)
    double routerPositions[17][2] = {
        { 120.0,  45.0}, // R0
        { 110.0, -30.0}, // R1
        {  85.0, -75.0}, // R2
        {  40.0,-110.0}, // R3
        { -20.0,-130.0}, // R4
        { -75.0,-100.0}, // R5
        {-110.0, -60.0}, // R6
        {-130.0,  -5.0}, // R7
        {-125.0,  40.0}, // R8
        { -90.0,  90.0}, // R9
        { -45.0, 115.0}, // R10
        {  15.0, 125.0}, // R11
        {  65.0, 105.0}, // R12
        { 100.0,  70.0}, // R13
        {  25.0,  25.0}, // R14
        { -30.0, -20.0}, // R15
        {  10.0, -40.0}  // R16
    };

    int activeCount = 0; 
    for (uint32_t i = 0; i < 17; ++i) {
        apPosAlloc->Add (Vector (routerPositions[i][0], routerPositions[i][1], 10.0));
        if (activeMask[i] == '1') activeCount++;
    }
    
    apMobility.SetPositionAllocator (apPosAlloc);
    apMobility.SetMobilityModel ("ns3::ConstantPositionMobilityModel");
    apMobility.Install (apNodes);

    // Parabolic Antennas automatically calculated to point at the center (0,0)
    for (uint32_t i = 0; i < 17; ++i) {
        Ptr<ParabolicAntennaModel> antenna = CreateObject<ParabolicAntennaModel> ();
        double angleToCenterRad = std::atan2 (-routerPositions[i][1], -routerPositions[i][0]);
        antenna->SetAttribute ("Orientation", DoubleValue (angleToCenterRad * 180.0 / M_PI));
        antenna->SetAttribute ("Beamwidth", DoubleValue (45.0));
        apNodes.Get(i)->AggregateObject (antenna);
    }

    phy.Set("TxGain", DoubleValue(13.0)); 
    phy.Set("RxGain", DoubleValue(13.0));
    NetDeviceContainer apDevices;
    
    for (uint32_t i = 0; i < 17; ++i) {
        if (activeMask[i] == '0') {
            phy.Set ("TxPowerStart", DoubleValue (-100.0)); 
            phy.Set ("TxPowerEnd", DoubleValue (-100.0));
        } else {
            phy.Set ("TxPowerStart", DoubleValue (25.0));   
            phy.Set ("TxPowerEnd", DoubleValue (25.0));
        }
        apDevices.Add(wifi.Install (phy, mac, apNodes.Get(i)));
    }

    // ==========================================
    // 3. User Topology (Students in the center)
    // ==========================================
    MobilityHelper userMobility;
    userMobility.SetPositionAllocator ("ns3::RandomDiscPositionAllocator",
                                       "X", StringValue ("0.0"), "Y", StringValue ("0.0"),
                                       "Rho", StringValue ("ns3::UniformRandomVariable[Min=0|Max=50]"));
    userMobility.Install (userNodes);

    phy.Set("TxGain", DoubleValue(0.0));
    phy.Set("RxGain", DoubleValue(0.0));
    phy.Set ("TxPowerStart", DoubleValue (20.0)); 
    phy.Set ("TxPowerEnd", DoubleValue (20.0));
    NetDeviceContainer userDevices = wifi.Install (phy, mac, userNodes);

    // ==========================================
    // 4. Routing & Traffic Setup
    // ==========================================
    InternetStackHelper stack;
    stack.Install (apNodes);
    stack.Install (userNodes);

    Ipv4AddressHelper address;
    address.SetBase ("192.168.1.0", "255.255.255.0");
    
    NetDeviceContainer allDevices;
    allDevices.Add(apDevices);
    allDevices.Add(userDevices);
    Ipv4InterfaceContainer allInterfaces = address.Assign (allDevices);

    uint16_t port = 9;
    UdpServerHelper server (port);
    ApplicationContainer serverApps = server.Install (userNodes);
    serverApps.Start (Seconds (1.0));
    serverApps.Stop (Seconds (simTime));

    ApplicationContainer clientApps;
    for (uint32_t i = 0; i < 17; ++i) {
        if (activeMask[i] == '1') {
            UdpClientHelper client (allInterfaces.GetAddress (17 + (i % numUsers)), port);
            client.SetAttribute ("MaxPackets", UintegerValue (2000));
            client.SetAttribute ("Interval", TimeValue (MilliSeconds (10)));
            client.SetAttribute ("PacketSize", UintegerValue (1024));
            clientApps.Add(client.Install (apNodes.Get(i)));
        }
    }
    clientApps.Start (Seconds (2.0)); 
    clientApps.Stop (Seconds (simTime));

    // ==========================================
    // 5. Connect Trace Callback for SINR
    // ==========================================
    Config::Connect ("/NodeList/*/DeviceList/*/$ns3::WifiNetDevice/Phy/MonitorSnifferRx", MakeCallback (&MonitorSnifferRxCallback));

    // ==========================================
    // 6. Metrics & Output
    // ==========================================
    FlowMonitorHelper flowmon;
    Ptr<FlowMonitor> monitor = flowmon.InstallAll ();

    NS_LOG_UNCOND ("--> Thesis Scenario: " << activeCount << " Active Towers");
    NS_LOG_UNCOND ("--> Simulation started. Running for " << simTime << " seconds...");
    Simulator::Stop (Seconds (simTime));
    Simulator::Run ();

    monitor->CheckForLostPackets ();
    std::map<FlowId, FlowMonitor::FlowStats> stats = monitor->GetFlowStats ();

    double totalTxPackets = 0, totalRxPackets = 0, totalThroughput = 0;
    for (auto const& [flowId, flowStats] : stats) {
        totalTxPackets += flowStats.txPackets;
        totalRxPackets += flowStats.rxPackets;
        double flowDuration = flowStats.timeLastRxPacket.GetSeconds() - flowStats.timeFirstTxPacket.GetSeconds();
        if (flowDuration > 0) totalThroughput += (flowStats.rxBytes * 8.0) / (flowDuration * 1000000.0);
    }
    
    double packetLoss = (totalTxPackets > 0) ? ((totalTxPackets - totalRxPackets) / totalTxPackets) * 100.0 : 100.0;
    double averageSinr = (globalSinrSamples > 0) ? (globalTotalSinrDb / globalSinrSamples) : 0.0;
    
    // FORMATTED EXACTLY LIKE MANILA OUTPUT
    NS_LOG_UNCOND ("-------------------------------------------------");
    NS_LOG_UNCOND ("OPTIMIZATION RESULTS:");
    NS_LOG_UNCOND ("Active Towers: " << activeCount);
    NS_LOG_UNCOND ("Energy Score (Lower is better): " << CalculateTestbedEnergy(activeCount) << " Watts (Est)");
    NS_LOG_UNCOND ("System Throughput (Higher is better): " << totalThroughput << " Mbps");
    NS_LOG_UNCOND ("Average SINR (Higher is better): " << averageSinr << " dB");
    NS_LOG_UNCOND ("Packet Loss Ratio (Lower is better): " << packetLoss << " %");
    NS_LOG_UNCOND ("-------------------------------------------------\n");

    Simulator::Destroy ();
    return 0;
}
