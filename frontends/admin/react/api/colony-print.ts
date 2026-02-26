export interface LoginResponse {
    sid: string;
    session_id: string;
    username: string;
    tokens: string[];
}

export interface Account {
    username: string;
    email: string;
    type: number;
    tokens: string[];
}

export interface NodeInfo {
    name: string;
    location: string;
    mode: string;
    printer: string;
    engines: string[];
    engine_info: Record<string, Record<string, string>>;
    platform: string;
    os: string;
    version: string;
    last_ping?: number;
}

export interface JobInfo {
    id: string;
    name: string;
    node_id: string;
    data_length: number;
    type?: string;
    format?: string;
    options?: Record<string, unknown>;
    status: string;
    queued_time: number;
    printing_time?: number;
    finish_time?: number;
    result?: Record<string, unknown> & {
        output_data?: string;
        output_encoding?: string;
        output_mime_type?: string;
    };
}

export interface PrinterInfo {
    name: string;
    is_default: boolean;
    media: string;
    width: number;
    length: number;
}

export interface PingResponse {
    time: number;
}

export class ColonyPrintAPI {
    baseUrl: string;
    sessionId: string | null;
    username: string | null;

    constructor(options?: {
        baseUrl?: string;
        sessionId?: string | null;
        username?: string | null;
    }) {
        this.baseUrl = options?.baseUrl ?? "";
        this.sessionId = options?.sessionId ?? null;
        this.username = options?.username ?? null;
    }

    async login(
        username: string,
        password: string
    ): Promise<LoginResponse> {
        const response = await this._fetch("/api/admin/login", {
            method: "POST",
            headers: { "Content-Type": "application/x-www-form-urlencoded" },
            body: new URLSearchParams({ username, password })
        });
        const data = (await response.json()) as LoginResponse;
        this.sessionId = data.session_id;
        this.username = data.username;
        return data;
    }

    async logout(): Promise<void> {
        await this._fetch("/api/admin/logout", { method: "POST" });
        this.sessionId = null;
        this.username = null;
    }

    async me(): Promise<Account> {
        const response = await this._fetch("/api/admin/me_account");
        return (await response.json()) as Account;
    }

    async listNodes(): Promise<Record<string, NodeInfo>> {
        const response = await this._fetch("/nodes");
        return (await response.json()) as Record<string, NodeInfo>;
    }

    async getNode(id: string): Promise<NodeInfo> {
        const response = await this._fetch(`/nodes/${encodeURIComponent(id)}`);
        return (await response.json()) as NodeInfo;
    }

    async listJobs(): Promise<Record<string, JobInfo>> {
        const response = await this._fetch("/jobs");
        return (await response.json()) as Record<string, JobInfo>;
    }

    async getJob(id: string): Promise<JobInfo> {
        const response = await this._fetch(`/jobs/${encodeURIComponent(id)}`);
        return (await response.json()) as JobInfo;
    }

    async listPrinters(): Promise<PrinterInfo[]> {
        const response = await this._fetch("/printers");
        return (await response.json()) as PrinterInfo[];
    }

    async ping(): Promise<PingResponse> {
        const response = await this._fetch("/ping");
        return (await response.json()) as PingResponse;
    }

    async _fetch(path: string, options?: RequestInit): Promise<Response> {
        const url = `${this.baseUrl}${path}`;
        const headers: Record<string, string> = {};
        if (options?.headers) {
            Object.assign(headers, options.headers);
        }
        if (this.sessionId) {
            headers["X-Session-Id"] = this.sessionId;
        }
        const response = await fetch(url, {
            ...options,
            headers,
            credentials: "include"
        });
        if (!response.ok) {
            const text = await response.text().catch(() => "");
            throw new Error(
                text || `Request failed with status ${response.status}`
            );
        }
        return response;
    }
}
