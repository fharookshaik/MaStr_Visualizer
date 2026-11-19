import * as duckdb from '@duckdb/duckdb-wasm'

type QueryRow = Record<string, string | number | boolean | null>
type DataConnection = {
  db: duckdb.AsyncDuckDB
  conn: duckdb.AsyncDuckDBConnection
}

let connectionPromise: Promise<DataConnection> | null = null

async function getConnection(): Promise<DataConnection> {
  if (!connectionPromise) {
    connectionPromise = (async () => {
      const bundle = await duckdb.selectBundle(duckdb.getJsDelivrBundles())
      const workerUrl = URL.createObjectURL(new Blob([`importScripts("${bundle.mainWorker!}");`], { type: 'text/javascript' }))
      const worker = new Worker(workerUrl)
      const db = new duckdb.AsyncDuckDB(new duckdb.ConsoleLogger(), worker)
      await db.instantiate(bundle.mainModule, bundle.pthreadWorker)
      URL.revokeObjectURL(workerUrl)

      const conn = await db.connect()
      const parquetUrl = new URL(`${import.meta.env.BASE_URL}data/units.parquet`, window.location.href).toString()
      await db.registerFileURL('units.parquet', parquetUrl, duckdb.DuckDBDataProtocol.HTTP, false)
      return { db, conn }
    })().catch((error: unknown) => {
      connectionPromise = null
      throw error
    })
  }
  return connectionPromise
}

export async function queryUnits(sql: string): Promise<QueryRow[]> {
  const { conn } = await getConnection()
  const result = await conn.query(sql)
  return result.toArray().map((row) => row.toJSON() as QueryRow)
}

export async function closeDataConnection(): Promise<void> {
  if (!connectionPromise) return
  const connection = await connectionPromise.catch(() => null)
  connectionPromise = null
  if (connection) {
    await connection.conn.close()
    await connection.db.terminate()
  }
}
