import { ShieldCheck, Database, Cpu, Users } from 'lucide-react'
import { Card } from '../components/ui'
import { Breadcrumbs } from '../components/DataDisplay'
import { AIDisclaimer } from '../components/Insights'

export default function About() {
  return (
    <div className="max-w-content mx-auto px-4 sm:px-6 py-8">
      <Breadcrumbs items={[{ label: 'About' }]} />
      <h1 className="text-3xl font-semibold mb-3">About this platform</h1>
      <p className="text-ink-muted max-w-2xl mb-8">
        The Nyeri Accountability Platform is a final-year civic-technology project that consolidates public
        governance data for Nyeri County and uses AI to help residents, journalists and oversight bodies
        understand how public funds are managed.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-10">
        <InfoCard icon={Database} title="What data we use">
          County budgets, NG-CDF allocations, Auditor-General findings and departmental spending records,
          all drawn from publicly available government documents.
        </InfoCard>
        <InfoCard icon={Cpu} title="How the AI works">
          A model trained on historical governance data flags spending patterns that deviate from expected
          ranges, then LIME explains which factors drove each flag.
        </InfoCard>
        <InfoCard icon={ShieldCheck} title="What we don't do">
          We don't accuse anyone of wrongdoing. Every AI result is labelled as an indicator that needs human
          investigation, never a verdict.
        </InfoCard>
        <InfoCard icon={Users} title="Who this is for">
          Residents wanting to understand local spending, journalists investigating leads, civil society
          groups monitoring public funds, and oversight institutions.
        </InfoCard>
      </div>

      <AIDisclaimer />
    </div>
  )
}

function InfoCard({ icon: Icon, title, children }) {
  return (
    <Card className="p-6">
      <div className="flex h-9 w-9 items-center justify-center rounded bg-forest-50 text-forest-700 mb-3">
        <Icon size={18} />
      </div>
      <h3 className="font-serif font-semibold text-lg mb-2">{title}</h3>
      <p className="text-sm text-ink-muted">{children}</p>
    </Card>
  )
}
