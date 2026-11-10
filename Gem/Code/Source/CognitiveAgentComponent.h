#pragma once

#include <AzCore/Component/Component.h>
#include "CognitiveAgentBus.h"

namespace EdgeCloudContinuum
{
    class CognitiveAgentComponent 
        : public AZ::Component
        , public CognitiveAgentRequestBus::Handler
    {
    public:
        AZ_COMPONENT(CognitiveAgentComponent, "{7F1A8B2C-3E4D-5F6A-7B8C-9D0E1F2A3B4C}");

        static void Reflect(AZ::ReflectContext* context);

        void Init() override;
        void Activate() override;
        void Deactivate() override;

        void RegisterAgentState(uint32_t agentId, const AZ::Vector3& position, float velocity) override;
        void RequestFederatedSync(const AZ::Vector3& weightDeltaSummary) override;
    };
}
