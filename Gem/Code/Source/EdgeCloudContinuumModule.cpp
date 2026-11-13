#include <AzCore/Memory/SystemAllocator.h>
#include <AzCore/Module/Module.h>

#include "CognitiveAgentComponent.h"

namespace EdgeCloudContinuum
{
    class EdgeCloudContinuumModule : public AZ::Module
    {
    public:
        AZ_RTTI(EdgeCloudContinuumModule, "{083BFC95-60AB-4F6C-A615-D417D383D765}", AZ::Module);
        AZ_CLASS_ALLOCATOR(EdgeCloudContinuumModule, AZ::SystemAllocator);

        EdgeCloudContinuumModule()
            : AZ::Module()
        {
            m_descriptors.insert(m_descriptors.end(), {
                CognitiveAgentComponent::CreateDescriptor(),
            });
        }

        AZ::ComponentTypeList GetRequiredSystemComponents() const override
        {
            return AZ::ComponentTypeList{};
        }
    };
}

AZ_DECLARE_MODULE_CLASS(Gem_EdgeCloudContinuum, EdgeCloudContinuum::EdgeCloudContinuumModule)
