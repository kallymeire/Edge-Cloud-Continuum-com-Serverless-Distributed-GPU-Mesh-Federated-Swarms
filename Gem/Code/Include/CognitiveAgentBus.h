#pragma once

#include <AzCore/EBus/EBus.h>
#include <AzCore/Math/Vector3.h>

class CognitiveAgentInterface : public AZ::EBusTraits
{
public:
    static const AZ::EBusHandlerPolicy HandlerPolicy = AZ::EBusHandlerPolicy::Single;
    static const AZ::EBusAddressPolicy AddressPolicy = AZ::EBusAddressPolicy::Single;

    virtual void RegisterAgentState(uint32_t agentId, const AZ::Vector3& position, float velocity) = 0;
    virtual void RequestFederatedSync(const AZ::Vector3& weightDeltaSummary) = 0;
};

using CognitiveAgentRequestBus = AZ::EBus<CognitiveAgentInterface>;
