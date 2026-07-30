# HF Docker Space 适配层 —— 业务仍用官方 ncmm
FROM ghcr.io/3899/ncmm:latest

USER root

# alpine：python3 仅 keep-alive；curl 排障
RUN apk add --no-cache python3 curl ca-certificates tzdata \
    && cp /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone

ENV TZ=Asia/Shanghai \
    PORT=7860 \
    APP_PORT=7860 \
    CRON_1="30 8 * * * task" \
    CRON_2="0 14 * * * musician"

WORKDIR /data

RUN mkdir -p /opt/ncmm-hf /data

COPY configs/config.hf.yaml /opt/ncmm-hf/config.hf.yaml
COPY configs/notify.hf.yaml /opt/ncmm-hf/notify.hf.yaml
COPY scripts/keepalive.py /opt/ncmm-hf/keepalive.py
COPY scripts/bootstrap.sh /opt/ncmm-hf/bootstrap.sh

RUN chmod +x /opt/ncmm-hf/bootstrap.sh \
    && chmod +r /opt/ncmm-hf/keepalive.py /opt/ncmm-hf/config.hf.yaml /opt/ncmm-hf/notify.hf.yaml

# HF Space 健康检查端口
EXPOSE 7860

ENTRYPOINT ["/opt/ncmm-hf/bootstrap.sh"]
