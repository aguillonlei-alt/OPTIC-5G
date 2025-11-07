#include "ns3/mmwave-helper.h"
#include "ns3/mobility-helper.h"
#include "ns3/node-container.h"
#include <fstream>
#include <sstream>

using namespace ns3;

int main(int argc, char *argv[]) {
    NodeContainer enbNodes;
    MobilityHelper mobility;

    std::ifstream file("data/real_towers_ns3.csv");
    std::string line;
    double x, y;

    // Skip header
    getline(file, line);

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string token;
        getline(ss, token, ','); x = std::stod(token); // X
        getline(ss, token, ','); y = std::stod(token); // Y

        Ptr<Node> enb = CreateObject<Node>();
        Ptr<ListPositionAllocator> pos = CreateObject<ListPositionAllocator>();
        pos->Add(Vector(x, y, 30));  // 30 m tower height
        mobility.SetPositionAllocator(pos);
        mobility.Install(enb);

        enbNodes.Add(enb);
    }

    // Rest of NS-3 mmWave/LTE setup here
}
