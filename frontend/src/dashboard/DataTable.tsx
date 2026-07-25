interface Column<T> {
  key: string
  header: string
  render: (row: T) => string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  rows: T[]
  emptyLabel?: string
}

export function DataTable<T>({ columns, rows, emptyLabel = 'No rows.' }: DataTableProps<T>) {
  if (rows.length === 0) {
    return <p className="dash-empty">{emptyLabel}</p>
  }
  return (
    <div className="dash-table-wrap">
      <table className="dash-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key}>{col.header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map((col) => (
                <td key={col.key}>{col.render(row)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
