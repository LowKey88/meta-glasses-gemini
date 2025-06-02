import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Meta Glasses Dashboard',
  description: 'Admin dashboard for Meta Glasses Gemini',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}