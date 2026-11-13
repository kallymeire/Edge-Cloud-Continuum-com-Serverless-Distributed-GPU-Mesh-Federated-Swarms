#pragma once

#include <AzCore/Component/Component.h>
#include <EdgeCloudContinuum/CognitiveAgentBus.h>

namespace EdgeCloudContinuum
{
    class CognitiveAgentComponent
        : public AZ::Component
        , protected CognitiveAgentRequestBus::Handler
    {
    public:
        AZ_COMPONENT(CognitiveAgentComponent, "{2208A4DE-14B8-4C50-AE1B-7DC1E8744D5D}");

        static void Reflect(AZ::ReflectContext* context);
        static void GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided);

        // AZ::Component
        void Init() override;
        void Activate() override;
        void Deactivate() override;

        // CognitiveAgentRequestBus
        void RegisterAgentState(AZ::u32 agentId, const AZ::Vector3& position, float velocity) override;
        void RequestFederatedSync(const AZ::Vector3& weightDeltaSummary) override;
    };
}
