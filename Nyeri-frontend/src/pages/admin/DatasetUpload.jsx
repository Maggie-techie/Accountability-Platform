import { useState } from 'react'
import { UploadCloud, CheckCircle2, AlertTriangle, ChevronRight, ChevronLeft, FileSpreadsheet } from 'lucide-react'
import { Card, Badge, Button, Alert } from '../../components/ui'
import { Select } from '../../components/Filters'

const steps = ['Select dataset', 'Upload file', 'Category & scope', 'Preview', 'Validate', 'Confirm']

export default function DatasetUpload() {
  const [step, setStep] = useState(0)
  const [fileName, setFileName] = useState('')
  const [category, setCategory] = useState('')
  const [county, setCounty] = useState('Nyeri')
  const [fy, setFy] = useState('')

  function next() { setStep((s) => Math.min(s + 1, steps.length - 1)) }
  function back() { setStep((s) => Math.max(s - 1, 0)) }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Dataset upload</h1>
      <p className="text-ink-muted mb-6">Import a new governance dataset into the platform.</p>

      {/* Stepper */}
      <div className="flex items-center gap-1 mb-8 overflow-x-auto pb-1">
        {steps.map((s, i) => (
          <div key={s} className="flex items-center gap-1 shrink-0">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium ${
              i === step ? 'bg-forest-700 text-white' : i < step ? 'bg-forest-50 text-forest-700' : 'bg-ink/5 text-ink-faint'
            }`}>
              {i < step ? <CheckCircle2 size={13} /> : <span>{i + 1}</span>} {s}
            </div>
            {i < steps.length - 1 && <ChevronRight size={14} className="text-ink-faint" />}
          </div>
        ))}
      </div>

      <Card className="p-6 max-w-2xl">
        {step === 0 && (
          <StepBody title="What kind of dataset are you importing?">
            <div className="grid grid-cols-2 gap-3">
              {['County Finance', 'NG-CDF Allocations', 'Audit Findings', 'Departmental Spending'].map((c) => (
                <button
                  key={c}
                  onClick={() => { setCategory(c); next() }}
                  className="text-left rounded-md border border-line p-4 hover:border-forest-400 hover:bg-forest-50/40 text-sm font-medium"
                >
                  {c}
                </button>
              ))}
            </div>
          </StepBody>
        )}

        {step === 1 && (
          <StepBody title={`Upload your ${category} file`}>
            <label className="flex flex-col items-center justify-center gap-2 border-2 border-dashed border-line rounded-md py-10 cursor-pointer hover:border-forest-400">
              <UploadCloud size={28} className="text-ink-faint" />
              <span className="text-sm text-ink-muted">{fileName || 'Click to choose a CSV or Excel file'}</span>
              <input type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={(e) => setFileName(e.target.files?.[0]?.name || '')} />
            </label>
            <StepNav back={back} next={next} nextDisabled={!fileName} />
          </StepBody>
        )}

        {step === 2 && (
          <StepBody title="Category and scope">
            <div className="grid grid-cols-2 gap-4">
              <Select label="County" value={county} onChange={setCounty} options={['Nyeri']} />
              <Select label="Financial year" value={fy} onChange={setFy} options={['2022/23', '2023/24', '2024/25', '2025/26']} />
            </div>
            <StepNav back={back} next={next} nextDisabled={!fy} />
          </StepBody>
        )}

        {step === 3 && (
          <StepBody title="Preview data">
            <div className="flex items-center gap-2 text-sm text-ink-muted mb-3">
              <FileSpreadsheet size={16} /> {fileName} &middot; {category} &middot; FY {fy}
            </div>
            <div className="border border-line rounded overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-ink/5"><tr><th className="p-2 text-left">Constituency</th><th className="p-2 text-left">MP</th><th className="p-2 text-left">FY24/25</th></tr></thead>
                <tbody>
                  <tr className="border-t border-line"><td className="p-2">Tetu</td><td className="p-2">Hon. Geoffrey Wandeto</td><td className="p-2">161.5</td></tr>
                  <tr className="border-t border-line"><td className="p-2">Kieni</td><td className="p-2">Hon. Njoroge Wainaina</td><td className="p-2">206.6</td></tr>
                </tbody>
              </table>
            </div>
            <StepNav back={back} next={next} />
          </StepBody>
        )}

        {step === 4 && (
          <StepBody title="Validation results">
            <Alert tone="warning" title="2 warnings found">Review these before importing. You can still proceed.</Alert>
            <ul className="mt-4 space-y-2 text-sm">
              <li className="flex items-center gap-2 text-forest-700"><CheckCircle2 size={15} /> 24 records passed validation</li>
              <li className="flex items-center gap-2 text-gold-500"><AlertTriangle size={15} /> 1 row has an inconsistent financial-year label</li>
              <li className="flex items-center gap-2 text-gold-500"><AlertTriangle size={15} /> 1 duplicate constituency entry detected</li>
            </ul>
            <StepNav back={back} next={next} nextLabel="Proceed to import" />
          </StepBody>
        )}

        {step === 5 && (
          <div className="text-center py-6">
            <CheckCircle2 size={36} className="mx-auto text-forest-600 mb-3" />
            <p className="font-serif font-semibold text-lg text-ink mb-1">Import successful</p>
            <p className="text-sm text-ink-muted mb-4">24 records were added to the database and are now live on the public platform.</p>
            <Badge tone="good">Dataset: {category} &middot; FY {fy}</Badge>
          </div>
        )}
      </Card>
    </div>
  )
}

function StepBody({ title, children }) {
  return (
    <div>
      <h3 className="font-serif font-semibold text-lg mb-4">{title}</h3>
      {children}
    </div>
  )
}

function StepNav({ back, next, nextDisabled, nextLabel = 'Continue' }) {
  return (
    <div className="flex justify-between mt-6 pt-4 border-t border-line">
      <Button variant="ghost" onClick={back}><ChevronLeft size={15} /> Back</Button>
      <Button onClick={next} disabled={nextDisabled}>{nextLabel}</Button>
    </div>
  )
}
