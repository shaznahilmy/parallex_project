import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Home from '@/pages/Home.jsx'
import Results from '@/pages/Results.jsx'

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/results" element={<Results />} />
      </Routes>
    </Router>
  )
}
