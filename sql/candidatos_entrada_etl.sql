WITH REFERENCIAS AS (
    SELECT r.MARCA,
           r.RUT,
           TO_CHAR(r.ID_DOC_PPL) AS ID_DOC_PPL_TXT,
           r.TIPO_DOC,
           r.EMISION,
           r.CURRENT_TOTAL,
           ROW_NUMBER() OVER (
               PARTITION BY r.MARCA, r.RUT, TO_CHAR(r.ID_DOC_PPL)
               ORDER BY r.EMISION DESC NULLS LAST,
                        r.MOD_T DESC NULLS LAST,
                        r.CREATED_T DESC NULLS LAST
           ) AS RN
    FROM SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1 r
    WHERE r.ID_DOC_PPL IS NOT NULL
),
CANDIDATOS AS (
    SELECT CASE
               WHEN UPPER(t.FOLIO) LIKE '%CB1-%' THEN 'CB1'
               WHEN UPPER(t.FOLIO) LIKE '%B1-%' THEN 'B1'
               ELSE 'OTRO'
           END AS TIPO_B1,
           t.MARCA,
           t.TIPO_SUSCRIPTOR,
           t.TIPO_EMISION_SET,
           t.ACCOUNT_NO,
           t.RUT,
           t.FOLIO,
           t.TIPO_DOC,
           t.EMISION,
           t.VENCIMIENTO,
           t.CURRENT_TOTAL,
           t.WRITEOFF,
           t.DUE,
           t.NAME,
           t.NOMBRE_CLARO,
           t.MONTO_NC,
           t.FOLIO_REBAJADO,
           t.MONTO_FOLIO_REBAJADO,
           ref.TIPO_DOC AS REF_TIPO_DOC,
           ref.EMISION AS REF_EMISION,
           ref.CURRENT_TOTAL AS REF_CURRENT_TOTAL
    FROM SCBILL.HP_CONSOLIDADO_ANDES_VTR_B1 t
    LEFT JOIN REFERENCIAS ref
      ON ref.RN = 1
     AND ref.MARCA = t.MARCA
     AND ref.RUT = t.RUT
     AND ref.ID_DOC_PPL_TXT = TRIM(TO_CHAR(t.FOLIO_REBAJADO))
    WHERE (UPPER(t.FOLIO) LIKE '%B1-%' OR UPPER(t.FOLIO) LIKE '%CB1-%')
      AND NVL(t.CURRENT_TOTAL, 0) > 0
      AND NVL(t.DUE, 0) > 0
      AND t.MARCA IN ('CLARO', 'VTR')
      AND t.TIPO_DOC IN (33, 39)
      AND t.TIPO_SUSCRIPTOR IN ('Fijo', 'Movil')
      AND NVL(t.CURRENT_TOTAL, 0) + NVL(t.WRITEOFF, 0) > 0
      AND t.EMISION >= :p_fecha_desde
      AND t.EMISION < :p_fecha_hasta
      AND TRUNC(t.VENCIMIENTO) = TRUNC(SYSDATE) + :p_dias_para_vencimiento
      AND ((t.TIPO_EMISION_SET = 'Bill Masivo'
            AND t.EMISION < SYSDATE - :p_dias_espera_bill_masivo)
           OR (NVL(t.TIPO_EMISION_SET, 'SIN TIPO') <> 'Bill Masivo'
               AND t.EMISION < SYSDATE))
)
SELECT c.MARCA AS MARCA,
       CASE
           WHEN c.MARCA = 'CLARO' THEN :p_rut_emisor_claro
           WHEN c.MARCA = 'VTR' THEN :p_rut_emisor_vtr
       END AS RUT_EMISOR,
       CASE WHEN c.TIPO_B1 = 'CB1' THEN 61 ELSE c.TIPO_DOC END AS TIPO_DOC,
       c.TIPO_SUSCRIPTOR AS TIPO_SUSCRIPTOR,
       c.RUT AS RUT_CLIENTE,
       COALESCE(TRIM(c.NOMBRE_CLARO), TRIM(c.NAME), TRIM(:p_nombre_default)) AS NOMBRE,
       TRIM(:p_giro_default) AS GIRO,
       TRIM(:p_direccion_default) AS DIRECCION,
       TRIM(:p_comuna_default) AS COMUNA,
       TRIM(:p_ciudad_default) AS CIUDAD,
       c.FOLIO AS BILL_NO,
       TRUNC(c.EMISION) AS EMISION,
       CASE
           WHEN c.TIPO_B1 = 'CB1'
               THEN COALESCE(c.MONTO_FOLIO_REBAJADO, c.REF_CURRENT_TOTAL)
           ELSE c.CURRENT_TOTAL
       END AS MONTO_DOC,
       TRIM(:p_email_default) AS EMAIL,
       CASE
           WHEN c.TIPO_B1 = 'CB1' THEN COALESCE(c.REF_TIPO_DOC, c.TIPO_DOC)
       END AS TIPO_DOC_REF,
       CASE WHEN c.TIPO_B1 = 'CB1' THEN c.FOLIO_REBAJADO END AS FOLIO_REBAJADO,
       CASE
           WHEN c.TIPO_B1 = 'CB1'
               THEN COALESCE(
                   TRUNC(c.REF_EMISION),
                   CASE
                       WHEN :p_usar_emision_candidato_como_ref = 1 THEN TRUNC(c.EMISION)
                   END
               )
       END AS EMISION_BOLETA,
       CASE WHEN c.TIPO_B1 = 'CB1' THEN ABS(c.MONTO_NC) END AS MONTO_NCRD
FROM CANDIDATOS c
ORDER BY c.VENCIMIENTO, c.TIPO_B1, c.MARCA, c.ACCOUNT_NO, c.FOLIO
