FROM maven:3.9-eclipse-temurin-21-alpine AS build

WORKDIR /app

COPY pom.xml ./
RUN mvn -B -q -DskipTests dependency:go-offline

COPY src ./src

RUN mvn -B -q -DskipTests package

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

RUN addgroup -S app && adduser -S app -G app \
    && apk add --no-cache curl \
    && mkdir -p /app/data/evidence \
    && chown -R app:app /app

COPY --from=build /app/target/*.jar app.jar

USER app

EXPOSE 9090

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
