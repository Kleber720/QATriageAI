import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  clearTicketHistory,
  deleteTicketFromHistory,
  loadTicketHistory,
  MAX_TICKET_HISTORY_ENTRIES,
  saveTicketToHistory,
  TICKET_HISTORY_STORAGE_KEY,
  type StorageLike,
} from "../src/lib/ticketHistory.ts";
import type { QATicket } from "../src/types/triage.ts";

class MemoryStorage implements StorageLike {
  private map = new Map<string, string>();

  getItem(key: string): string | null {
    return this.map.get(key) ?? null;
  }

  setItem(key: string, value: string): void {
    this.map.set(key, value);
  }

  removeItem(key: string): void {
    this.map.delete(key);
  }
}

function makeTicket(titulo: string): QATicket {
  return {
    titulo,
    categoria: "bug_funcional",
    etapas_para_reproduzir: ["Acesse YouShop", "É aqui que o bug é observado"],
    resultado_atual: "Cupom removido",
    resultado_esperado: "Cupom mantido",
    descricao: "Descrição do defeito no checkout",
    taxa_de_reproducao: "Não informado",
    notas: "N/A",
    o_que_nao_foi_confirmado: [],
    correcoes_ortograficas: [],
    dados_sensiveis_removidos: [],
    score_antes: 20,
    score_depois: 70,
    checklist_final: [],
    platform_context_used: null,
    origem_dos_dados: [],
    divergencias_com_logs: [],
  };
}

describe("ticketHistory", () => {
  it("salva entradas mais recentes primeiro e limita em 20 itens", () => {
    const storage = new MemoryStorage();
    for (let i = 1; i <= MAX_TICKET_HISTORY_ENTRIES + 3; i += 1) {
      saveTicketToHistory(
        {
          originalReport: `Relato ${i}`,
          ticket: makeTicket(`Ticket ${i}`),
        },
        storage
      );
    }

    const loaded = loadTicketHistory(storage);
    assert.equal(loaded.length, MAX_TICKET_HISTORY_ENTRIES);
    assert.equal(loaded[0].ticket.titulo, `Ticket ${MAX_TICKET_HISTORY_ENTRIES + 3}`);
  });

  it("remove entrada individual e limpa todo o histórico", () => {
    const storage = new MemoryStorage();
    saveTicketToHistory(
      { originalReport: "R1", ticket: makeTicket("T1") },
      storage
    );
    const afterSecond = saveTicketToHistory(
      { originalReport: "R2", ticket: makeTicket("T2") },
      storage
    );

    const removed = deleteTicketFromHistory(afterSecond[0].id, storage);
    assert.equal(removed.length, 1);
    assert.equal(removed[0].ticket.titulo, "T1");

    const cleared = clearTicketHistory(storage);
    assert.equal(cleared.length, 0);
    assert.equal(loadTicketHistory(storage).length, 0);
  });

  it("retorna lista vazia se o JSON armazenado estiver corrompido", () => {
    const storage = new MemoryStorage();
    storage.setItem(TICKET_HISTORY_STORAGE_KEY, "{json-invalido");
    assert.deepEqual(loadTicketHistory(storage), []);
  });
});
