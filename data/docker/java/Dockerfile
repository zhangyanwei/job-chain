FROM java:8
MAINTAINER www.zhongwang.com

RUN mkdir /data && touch /data/app.jar
ADD app.jar /data/app.jar

COPY wait-for.sh wait-for.sh
RUN chmod +x wait-for.sh

CMD java -jar /data/app.jar