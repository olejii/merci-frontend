/* eslint-disable */
/* tslint:disable */
// @ts-nocheck
/*
 * ---------------------------------------------------------------
 * ## THIS FILE WAS GENERATED VIA SWAGGER-TYPESCRIPT-API        ##
 * ##                                                           ##
 * ## AUTHOR: acacode                                           ##
 * ## SOURCE: https://github.com/acacode/swagger-typescript-api ##
 * ---------------------------------------------------------------
 */

export interface QRPayload {
  /** @pattern ^m_[0-9]{3}$ */
  merchant_id: string;
  /** @pattern ^e_[0-9]{3}$ */
  employee_id: string;
  /** @pattern ^[a-f0-9]{6}$ */
  nonce: string;
  /** @format date-time */
  exp: string;
  /** @pattern ^[a-f0-9]{16}$ */
  signature: string;
}

export interface QRResponse {
  /** @example "qr_001" */
  qr_id: string;
  /** @pattern ^m_[0-9]{3}$ */
  merchant_id: string;
  merchant_name: string;
  /** @pattern ^e_[0-9]{3}$ */
  employee_id: string;
  employee_name: string;
  employee_role: "WAITER" | "BARTENDER" | "HOSTESS";
  employee_role_label: string;
  currency: string;
  payment_methods: {
    value: "SBP" | "CARD" | "SBERPAY";
    label: string;
    bank_fee_percent: 2 | 5;
  }[];
  compliment_options: {
    value: "FRIENDLY" | "ATTENTIVE" | "FAST" | "PROFESSIONAL" | "HOSPITABLE";
    label: string;
  }[];
  active_goals: TipGoal[];
  payment_url: string;
  employee_photo_url: string;
  /** @format date-time */
  exp: string;
}

export interface TipCreate {
  qr_id: string;
  /**
   * Сумма именно чаевых
   * @pattern ^[0-9]+\.[0-9]{2}$
   * @example "100.00"
   */
  tip_amount: string;
  payment_method: "SBP" | "CARD" | "SBERPAY";
  /** true: client pays bank fee on top; false: fee is deducted from employee's tip. */
  cover_service_fee?: boolean;
  goal_id?: string | null;
  /**
   * @min 1
   * @max 5
   */
  service_rating?: number | null;
  /**
   * @min 1
   * @max 5
   */
  restaurant_rating?: number | null;
  /** @maxLength 500 */
  restaurant_comment?: string;
  compliments?: (
    | "FRIENDLY"
    | "ATTENTIVE"
    | "FAST"
    | "PROFESSIONAL"
    | "HOSPITABLE"
  )[];
  /** @deprecated Use compliments to select one or more options. */
  compliment?:
    | "FRIENDLY"
    | "ATTENTIVE"
    | "FAST"
    | "PROFESSIONAL"
    | "HOSPITABLE";
  /** @maxLength 500 */
  employee_comment?: string;
  /**
   * @minLength 16
   * @maxLength 128
   */
  idempotency_key: string;
}

export interface Payment {
  /** @pattern ^p_[0-9]{4,8}$ */
  payment_id: string;
  status: "CREATED" | "PENDING" | "SUCCESS" | "DECLINED" | "CANCELED";
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  amount_total: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  tip_amount: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  service_fee_amount: string;
  payment_method: "SBP" | "CARD" | "SBERPAY";
  goal_id: string | null;
  compliments: (
    | "FRIENDLY"
    | "ATTENTIVE"
    | "FAST"
    | "PROFESSIONAL"
    | "HOSPITABLE"
  )[];
  bank_fee_percent: 2 | 5;
  commission_payer: "CLIENT" | "EMPLOYEE";
  employee_net_amount: string;
  confirm_token: string | null;
  error_code: string | null;
}

export interface Report {
  /** @pattern ^m_[0-9]{3}$ */
  merchant_id: string;
  /** @example "2025-11-01-2025-11-30" */
  period: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  tips_total: string;
  /** @min 0 */
  payments_count: number;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  avg_tip_amount: string;
  /**
   * @format double
   * @min 0
   * @max 1
   */
  success_rate: number;
}

export interface EmployeeReport {
  /** @pattern ^e_[0-9]{3}$ */
  employee_id: string;
  /** @example "2025-11-01-2025-11-30" */
  period: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  tips_total: string;
  /** @min 0 */
  payments_count: number;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  avg_tip_amount: string;
  /** @format date */
  top_day: string | null;
}

export interface TipGoal {
  goal_id: string;
  employee_id: string;
  title: string;
  description: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  target_amount: string;
  /** @pattern ^[0-9]+\.[0-9]{2}$ */
  collected_amount: string;
  /**
   * @min 0
   * @max 100
   */
  progress_pct: number;
  is_active: boolean;
}

export interface Error {
  error_code: string;
  message: string;
  retryable?: boolean;
  details?: Record<string, any>;
}

export type QueryParamsType = Record<string | number, any>;
export type ResponseFormat = keyof Omit<Body, "body" | "bodyUsed">;

export interface FullRequestParams extends Omit<RequestInit, "body"> {
  /** set parameter to `true` for call `securityWorker` for this request */
  secure?: boolean;
  /** request path */
  path: string;
  /** content type of request body */
  type?: ContentType;
  /** query params */
  query?: QueryParamsType;
  /** format of response (i.e. response.json() -> format: "json") */
  format?: ResponseFormat;
  /** request body */
  body?: unknown;
  /** base url */
  baseUrl?: string;
  /** request cancellation token */
  cancelToken?: CancelToken;
}

export type RequestParams = Omit<
  FullRequestParams,
  "body" | "method" | "query" | "path"
>;

export interface ApiConfig<SecurityDataType = unknown> {
  baseUrl?: string;
  baseApiParams?: Omit<RequestParams, "baseUrl" | "cancelToken" | "signal">;
  securityWorker?: (
    securityData: SecurityDataType | null,
  ) => Promise<RequestParams | void> | RequestParams | void;
  customFetch?: typeof fetch;
}

export interface HttpResponse<D extends unknown, E extends unknown = unknown>
  extends Response {
  data: D;
  error: E;
}

type CancelToken = Symbol | string | number;

export enum ContentType {
  Json = "application/json",
  JsonApi = "application/vnd.api+json",
  FormData = "multipart/form-data",
  UrlEncoded = "application/x-www-form-urlencoded",
  Text = "text/plain",
}

export class HttpClient<SecurityDataType = unknown> {
  public baseUrl: string =
    "https://tatarllc.ru";
  private securityData: SecurityDataType | null = null;
  private securityWorker?: ApiConfig<SecurityDataType>["securityWorker"];
  private abortControllers = new Map<CancelToken, AbortController>();
  private customFetch = (...fetchParams: Parameters<typeof fetch>) =>
    fetch(...fetchParams);

  private baseApiParams: RequestParams = {
    credentials: "include",
    headers: {},
    redirect: "follow",
    referrerPolicy: "no-referrer",
  };

  constructor(apiConfig: ApiConfig<SecurityDataType> = {}) {
    Object.assign(this, apiConfig);
  }

  public setSecurityData = (data: SecurityDataType | null) => {
    this.securityData = data;
  };

  protected encodeQueryParam(key: string, value: any) {
    const encodedKey = encodeURIComponent(key);
    return `${encodedKey}=${encodeURIComponent(typeof value === "number" ? value : `${value}`)}`;
  }

  protected addQueryParam(query: QueryParamsType, key: string) {
    return this.encodeQueryParam(key, query[key]);
  }

  protected addArrayQueryParam(query: QueryParamsType, key: string) {
    const value = query[key];
    return value.map((v: any) => this.encodeQueryParam(key, v)).join("&");
  }

  protected toQueryString(rawQuery?: QueryParamsType): string {
    const query = rawQuery || {};
    const keys = Object.keys(query).filter(
      (key) => "undefined" !== typeof query[key],
    );
    return keys
      .map((key) =>
        Array.isArray(query[key])
          ? this.addArrayQueryParam(query, key)
          : this.addQueryParam(query, key),
      )
      .join("&");
  }

  protected addQueryParams(rawQuery?: QueryParamsType): string {
    const queryString = this.toQueryString(rawQuery);
    return queryString ? `?${queryString}` : "";
  }

  private contentFormatters: Record<ContentType, (input: any) => any> = {
    [ContentType.Json]: (input: any) =>
      input !== null && (typeof input === "object" || typeof input === "string")
        ? JSON.stringify(input)
        : input,
    [ContentType.JsonApi]: (input: any) =>
      input !== null && (typeof input === "object" || typeof input === "string")
        ? JSON.stringify(input)
        : input,
    [ContentType.Text]: (input: any) =>
      input !== null && typeof input !== "string"
        ? JSON.stringify(input)
        : input,
    [ContentType.FormData]: (input: any) => {
      if (input instanceof FormData) {
        return input;
      }

      return Object.keys(input || {}).reduce((formData, key) => {
        const property = input[key];
        formData.append(
          key,
          property instanceof Blob
            ? property
            : typeof property === "object" && property !== null
              ? JSON.stringify(property)
              : `${property}`,
        );
        return formData;
      }, new FormData());
    },
    [ContentType.UrlEncoded]: (input: any) => this.toQueryString(input),
  };

  protected mergeRequestParams(
    params1: RequestParams,
    params2?: RequestParams,
  ): RequestParams {
    return {
      ...this.baseApiParams,
      ...params1,
      ...(params2 || {}),
      headers: {
        ...(this.baseApiParams.headers || {}),
        ...(params1.headers || {}),
        ...((params2 && params2.headers) || {}),
      },
    };
  }

  protected createAbortSignal = (
    cancelToken: CancelToken,
  ): AbortSignal | undefined => {
    if (this.abortControllers.has(cancelToken)) {
      const abortController = this.abortControllers.get(cancelToken);
      if (abortController) {
        return abortController.signal;
      }
      return void 0;
    }

    const abortController = new AbortController();
    this.abortControllers.set(cancelToken, abortController);
    return abortController.signal;
  };

  public abortRequest = (cancelToken: CancelToken) => {
    const abortController = this.abortControllers.get(cancelToken);

    if (abortController) {
      abortController.abort();
      this.abortControllers.delete(cancelToken);
    }
  };

  public request = async <T = any, E = any>({
    body,
    secure,
    path,
    type,
    query,
    format,
    baseUrl,
    cancelToken,
    ...params
  }: FullRequestParams): Promise<HttpResponse<T, E>> => {
    const secureParams =
      ((typeof secure === "boolean" ? secure : this.baseApiParams.secure) &&
        this.securityWorker &&
        (await this.securityWorker(this.securityData))) ||
      {};
    const requestParams = this.mergeRequestParams(params, secureParams);
    const queryString = query && this.toQueryString(query);
    const payloadFormatter = this.contentFormatters[type || ContentType.Json];
    const responseFormat = format || requestParams.format;

    return this.customFetch(
      `${baseUrl || this.baseUrl || ""}${path}${queryString ? `?${queryString}` : ""}`,
      {
        ...requestParams,
        headers: {
          ...(requestParams.headers || {}),
          ...(type && type !== ContentType.FormData
            ? { "Content-Type": type }
            : {}),
        },
        signal:
          (cancelToken
            ? this.createAbortSignal(cancelToken)
            : requestParams.signal) || null,
        body:
          typeof body === "undefined" || body === null
            ? null
            : payloadFormatter(body),
      },
    ).then(async (response) => {
      const r = response as HttpResponse<T, E>;
      r.data = null as unknown as T;
      r.error = null as unknown as E;

      const responseToParse = responseFormat ? response.clone() : response;
      const data = !responseFormat
        ? r
        : await responseToParse[responseFormat]()
            .then((data) => {
              if (r.ok) {
                r.data = data;
              } else {
                r.error = data;
              }
              return r;
            })
            .catch((e) => {
              r.error = e;
              return r;
            });

      if (cancelToken) {
        this.abortControllers.delete(cancelToken);
      }

      if (!response.ok) throw data;
      return data;
    });
  };
}

/**
 * @title Tips Platform
 * @version 1.0.0
 * @baseUrl https://tatarllc.ru
 *
 * Онлайн-чаевые для сети «Вкус-Сервис»
 */
export class Api<
  SecurityDataType extends unknown,
> extends HttpClient<SecurityDataType> {
  pay = {
    /**
     * @description Публичный JSON API по ссылке из QR. Возвращает данные сотрудника, ресторана, активные цели сбора и ссылку оплаты.
     *
     * @name GetPay
     * @summary Получить данные оплаты по QR
     * @request GET:/pay/
     */
    getPay: (
      query: {
        qr: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<QRResponse, Error>({
        path: `/pay/`,
        method: "GET",
        query: query,
        format: "json",
        ...params,
      }),
  };
  health = {
    /**
     * No description
     *
     * @name HealthList
     * @summary Проверка живости
     * @request GET:/health
     */
    healthList: (params: RequestParams = {}) =>
      this.request<
        {
          status: string;
          csrfToken: string;
        },
        Error
      >({
        path: `/health`,
        method: "GET",
        format: "json",
        ...params,
      }),
  };
  api = {
    /**
     * @description Получите CSRF-token запросом GET /health и передавайте его в X-CSRFToken.
     *
     * @name V1AuthLoginCreate
     * @summary Вход сотрудника или владельца мерчанта
     * @request POST:/api/v1/auth/login
     */
    v1AuthLoginCreate: (
      data: {
        /**
         * @format email
         * @maxLength 254
         */
        email: string;
        /** @format password */
        password: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          status: string;
          user_id: number;
        },
        Error
      >({
        path: `/api/v1/auth/login`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1AuthLogoutCreate
     * @summary Выход из учётной записи
     * @request POST:/api/v1/auth/logout
     * @secure
     */
    v1AuthLogoutCreate: (params: RequestParams = {}) =>
      this.request<
        {
          status: string;
        },
        Error
      >({
        path: `/api/v1/auth/logout`,
        method: "POST",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1MerchantsRegisterCreate
     * @summary Подать заявку на регистрацию мерчанта
     * @request POST:/api/v1/merchants/register
     */
    v1MerchantsRegisterCreate: (
      data: {
        /**
         * @minLength 1
         * @maxLength 100
         */
        name: string;
        /**
         * @format email
         * @maxLength 254
         */
        email: string;
        /** @pattern ^\+[1-9][0-9]{7,14}$ */
        phone: string;
        /**
         * @format password
         * @minLength 12
         */
        password: string;
        /** @maxLength 200 */
        description?: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          merchant_id: string;
          status: string;
          message: string;
        },
        Error
      >({
        path: `/api/v1/merchants/register`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1EmployeesCreate
     * @summary Пригласить сотрудника в заведение
     * @request POST:/api/v1/employees
     * @secure
     */
    v1EmployeesCreate: (
      data: {
        /** @maxLength 100 */
        name: string;
        /** @format email */
        email: string;
        /** @pattern ^\+[1-9][0-9]{7,14}$ */
        phone: string;
        role: "WAITER" | "BARTENDER" | "HOSTESS";
        /** @pattern ^[0-9]{4}$ */
        payout_last4: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          employee_id: string;
          status: string;
          invite_token: string;
          payment_details: string;
          role: "WAITER" | "BARTENDER" | "HOSTESS";
        },
        Error
      >({
        path: `/api/v1/employees`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1EmployeesAcceptCreate
     * @summary Принять приглашение сотрудника
     * @request POST:/api/v1/employees/{employee_id}/accept
     */
    v1EmployeesAcceptCreate: (
      employeeId: string,
      data: {
        invite_token: string;
        /**
         * @format password
         * @minLength 12
         */
        password: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          employee_id: string;
          status: string;
        },
        Error
      >({
        path: `/api/v1/employees/${employeeId}/accept`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * @description Для сотрудника или владельца активного мерчанта.
     *
     * @name V1QrCreate
     * @summary Создать подписанный QR и платёжную ссылку
     * @request POST:/api/v1/qr
     * @secure
     */
    v1QrCreate: (
      data: {
        employee_id: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<QRResponse, Error>({
        path: `/api/v1/qr`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1QrDetail
     * @summary Данные QR для формы чаевых
     * @request GET:/api/v1/qr/{qr_id}
     */
    v1QrDetail: (qrId: string, params: RequestParams = {}) =>
      this.request<QRResponse, Error>({
        path: `/api/v1/qr/${qrId}`,
        method: "GET",
        format: "json",
        ...params,
      }),

    /**
     * @name V1QrImageDetail
     * @summary Скачать PNG QR-кода
     * @request GET:/api/v1/qr/{qr_id}/image
     */
    v1QrImageDetail: (qrId: string, params: RequestParams = {}) =>
      this.request<Blob, Blob>({
        path: `/api/v1/qr/${qrId}/image`,
        method: "GET",
        format: "blob",
        ...params,
      }),

    /**
     * @name V1QrEmployeePhotoDetail
     * @summary Получить PNG-фото сотрудника или заглушку
     * @request GET:/api/v1/qr/{qr_id}/employee-photo
     */
    v1QrEmployeePhotoDetail: (qrId: string, params: RequestParams = {}) =>
      this.request<Blob, Blob>({
        path: `/api/v1/qr/${qrId}/employee-photo`,
        method: "GET",
        format: "blob",
        ...params,
      }),

    /**
     * @name V1QrEmployeePhotoUpdate
     * @summary Загрузить или обновить PNG-фото сотрудника
     * @request POST:/api/v1/qr/{qr_id}/employee-photo
     * @secure
     */
    v1QrEmployeePhotoUpdate: (
      qrId: string,
      data: {
        /** PNG image, max 5 MB */
        photo: Blob;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          employee_id: string;
          employee_photo_url: string;
        },
        Error
      >({
        path: `/api/v1/qr/${qrId}/employee-photo`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.FormData,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1TipsCreate
     * @summary Создать платёж с чаевыми
     * @request POST:/api/v1/tips
     */
    v1TipsCreate: (data: TipCreate, params: RequestParams = {}) =>
      this.request<Payment, Error>({
        path: `/api/v1/tips`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1GoalsCreate
     * @summary Создать цель сбора сотрудника
     * @request POST:/api/v1/goals
     * @secure
     */
    v1GoalsCreate: (
      data: {
        /** Передаёт владелец мерчанта для целей своих сотрудников */
        employee_id?: string;
        /** @maxLength 100 */
        title: string;
        /** @maxLength 300 */
        description?: string;
        /** @pattern ^[0-9]+\.[0-9]{2}$ */
        target_amount: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<TipGoal, Error>({
        path: `/api/v1/goals`,
        method: "POST",
        body: data,
        secure: true,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1EmployeesGoalsList
     * @summary Список целей сотрудника
     * @request GET:/api/v1/employees/{employee_id}/goals
     * @secure
     */
    v1EmployeesGoalsList: (employeeId: string, params: RequestParams = {}) =>
      this.request<
        {
          goals: TipGoal[];
        },
        Error
      >({
        path: `/api/v1/employees/${employeeId}/goals`,
        method: "GET",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1GoalsCloseCreate
     * @summary Закрыть цель сбора
     * @request POST:/api/v1/goals/{goal_id}/close
     * @secure
     */
    v1GoalsCloseCreate: (goalId: string, params: RequestParams = {}) =>
      this.request<TipGoal, Error>({
        path: `/api/v1/goals/${goalId}/close`,
        method: "POST",
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1PaymentsConfirmCreate
     * @summary Подтвердить платёж и запустить эмулятор шлюза
     * @request POST:/api/v1/payments/{id}/confirm
     */
    v1PaymentsConfirmCreate: (
      id: string,
      data: {
        confirm_token: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<Payment, Payment | Error>({
        path: `/api/v1/payments/${id}/confirm`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1PaymentsCancelCreate
     * @summary Отменить платёж до подтверждения
     * @request POST:/api/v1/payments/{id}/cancel
     */
    v1PaymentsCancelCreate: (
      id: string,
      data: {
        confirm_token: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<Payment, Error>({
        path: `/api/v1/payments/${id}/cancel`,
        method: "POST",
        body: data,
        type: ContentType.Json,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1ReportsTipsList
     * @summary Отчёт по чаевым мерчанта
     * @request GET:/api/v1/reports/tips
     * @secure
     */
    v1ReportsTipsList: (
      query: {
        /** Для владельца/администратора */
        merchant_id?: string;
        /** Только собственный отчёт сотрудника */
        employee_id?: string;
        /** @format date */
        from: string;
        /** @format date */
        to: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<Report | EmployeeReport, Error>({
        path: `/api/v1/reports/tips`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),

    /**
     * No description
     *
     * @name V1ReportsTipsDailyList
     * @summary Отчёт по чаевым в разрезе дней
     * @request GET:/api/v1/reports/tips/daily
     * @secure
     */
    v1ReportsTipsDailyList: (
      query: {
        merchant_id: string;
        /** @format date */
        from: string;
        /** @format date */
        to: string;
      },
      params: RequestParams = {},
    ) =>
      this.request<
        {
          merchant_id: string;
          daily: {
            /** @format date */
            date: string;
            /** @pattern ^[0-9]+\.[0-9]{2}$ */
            tips_total: string;
            payments_count: number;
            /** @pattern ^[0-9]+\.[0-9]{2}$ */
            avg_tip_amount: string;
          }[];
        },
        Error
      >({
        path: `/api/v1/reports/tips/daily`,
        method: "GET",
        query: query,
        secure: true,
        format: "json",
        ...params,
      }),
  };
}
