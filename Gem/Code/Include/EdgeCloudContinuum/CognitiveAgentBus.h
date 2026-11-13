#pragma once

#include <AzCore/base.h>
#include <AzCore/EBus/EBus.h>
#include <AzCore/Math/Vector3.h>

namespace EdgeCloudContinuum
{
    class CognitiveAgentInterface : public AZ::EBusTraits
    {
    public:
        virtual ~CognitiveAgentInterface() = default;

        static constexpr AZ::EBusHandlerPolicy HandlerPolicy = AZ::EBusHandlerPolicy::Single;
        static constexpr AZ::EBusAddressPolicy AddressPolicy = AZ::EBusAddressPolicy::Single;

        virtual void RegisterAgentState(AZ::u32 agentId, const AZ::Vector3& position, float velocity) = 0;

        // Placeholder: a Vector3 cannot carry real weight deltas. See Pipeline/core/federated_aggregator.py
        // for the actual update format (sparse indices + int8 values).
        virtual void RequestFederatedSync(const AZ::Vector3& weightDeltaSummary) = 0;
    };

    using CognitiveAgentRequestBus = AZ::EBus<CognitiveAgentInterface>;
}
