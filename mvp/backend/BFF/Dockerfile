# Stage 1: Base image for running the application

FROM mcr.microsoft.com/dotnet/aspnet:9.0@sha256:2b70ef1451cb01c2118969ad15fd0ae40fdbac158f09699fefae0dc32c4ca352 AS base
WORKDIR /app
EXPOSE 5054


# Stage 2: Build the project

FROM mcr.microsoft.com/dotnet/sdk:9.0@sha256:840f3b62b9742dde4461a3c31e38ffd34d41d7d33afd39c378cfcfd5dcb82bd5 AS build
WORKDIR /src
COPY BFF.csproj .
RUN dotnet restore
COPY . .
RUN dotnet build -c Release -o /app/build


# Stage 3: Publish the application

FROM build AS publish
RUN dotnet publish -c Release -o /app/publish


# Stage 4: Final image for running the application

FROM base AS final
WORKDIR /app
COPY --from=publish /app/publish .
ENTRYPOINT ["dotnet", "BFF.dll"]
