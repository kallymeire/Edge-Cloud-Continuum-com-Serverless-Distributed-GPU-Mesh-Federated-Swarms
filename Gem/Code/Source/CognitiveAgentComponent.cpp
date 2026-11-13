#include "CognitiveAgentComponent.h"

#include <AzCore/Debug/Trace.h>
#include <AzCore/Serialization/EditContext.h>
#include <AzCore/Serialization/SerializeContext.h>

namespace EdgeCloudContinuum
{
    void CognitiveAgentComponent::Reflect(AZ::ReflectContext* context)
    {
        if (auto serializeContext = azrtti_cast<AZ::SerializeContext*>(context))
        {
            serializeContext->Class<CognitiveAgentComponent, AZ::Component>()
                ->Version(1);

            if (AZ::EditContext* editContext = serializeContext->GetEditContext())
            {
                editContext->Class<CognitiveAgentComponent>(
                        "Cognitive Agent", "Receives agent state over CognitiveAgentRequestBus")
                    ->ClassElement(AZ::Edit::ClassElements::EditorData, "")
                        ->Attribute(AZ::Edit::Attributes::Category, "EdgeCloudContinuum")
                        ->Attribute(AZ::Edit::Attributes::AppearsInAddComponentMenu, AZ_CRC_CE("Game"));
            }
        }
    }

    void CognitiveAgentComponent::GetProvidedServices(AZ::ComponentDescriptor::DependencyArrayType& provided)
    {
        provided.push_back(AZ_CRC_CE("CognitiveAgentService"));
    }

    void CognitiveAgentComponent::Init() {}

    void CognitiveAgentComponent::Activate()
    {
        CognitiveAgentRequestBus::Handler::BusConnect();
    }

    void CognitiveAgentComponent::Deactivate()
    {
        CognitiveAgentRequestBus::Handler::BusDisconnect();
    }

    void CognitiveAgentComponent::RegisterAgentState(AZ::u32 agentId, const AZ::Vector3& position, float velocity)
    {
        AZ_Printf("CognitiveAgent", "Agent ID: %u | Position: X=%.2f Y=%.2f Z=%.2f | Vel: %.2f",
            agentId, position.GetX(), position.GetY(), position.GetZ(), velocity);
    }

    void CognitiveAgentComponent::RequestFederatedSync(const AZ::Vector3& weightDeltaSummary)
    {
        AZ_UNUSED(weightDeltaSummary);
        AZ_Printf("CognitiveAgent", "RequestFederatedSync called (stub: no network sync implemented)");
    }
}
